#include "tkm/tkm.hpp"

#include <cuda_runtime.h>

#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {
using GpuArchive = tkm::Archive<8u, 8u>;

struct Query {
    std::uint32_t object_index{};
    float seconds{};
    tkm::Guard guard{};
};

struct Output {
    tkm::QueryResult state{};
    tkm::GuardEvaluation guard{};
};

__global__ void query_kernel(
    const tkm::Seed* seeds,
    std::uint32_t seed_count,
    const GpuArchive* archive,
    const Query* queries,
    Output* outputs,
    std::uint32_t query_count) {
    const std::uint32_t index = blockIdx.x * blockDim.x + threadIdx.x;
    if (index >= query_count) return;
    const Query query = queries[index];
    Output output{};
    output.state = tkm::state_at(
        seeds, seed_count, *archive, query.object_index, query.seconds);
    if (output.state.status == tkm::QueryStatus::Ok) {
        output.guard = tkm::evaluate_guard(output.state.state, query.guard);
    }
    outputs[index] = output;
}

void check(cudaError_t status, const char* operation) {
    if (status != cudaSuccess) {
        throw std::runtime_error(std::string(operation) + ": " + cudaGetErrorString(status));
    }
}
}

int main() {
    try {
        const tkm::Seed host_seed{
            {0.0f, 0.0f, 0.0f}, 0.0f,
            {1.0f, 0.0f, 0.0f}, 0.1f,
            {0.0f, 0.0f, 0.0f}, 0.0f,
            1u, 0x1234u, 0u, 0u,
        };
        GpuArchive host_archive{};
        host_archive.segment_count = 1u;
        host_archive.segments[0].begin_seconds = 0.0f;
        host_archive.segments[0].end_seconds = 100.0f;
        host_archive.segments[0].origin_seconds = 0.0f;
        host_archive.segments[0].flags = tkm::kSegmentActive;
        host_archive.segments[0].lineage_seed = 0x5678u;

        constexpr std::uint32_t kQueries = 4096u;
        std::vector<Query> host_queries(kQueries);
        for (std::uint32_t i = 0u; i < kQueries; ++i) {
            host_queries[i].object_index = 0u;
            host_queries[i].seconds = static_cast<float>(i) * 0.01f;
            host_queries[i].guard.kind = tkm::GuardKind::PlaneSdf;
            host_queries[i].guard.a = {1.0f, 0.0f, 0.0f};
            host_queries[i].guard.b = -20.0f;
            host_queries[i].guard.event_margin = 1.0e-5f;
        }
        std::vector<Output> host_outputs(kQueries);

        tkm::Seed* device_seed = nullptr;
        GpuArchive* device_archive = nullptr;
        Query* device_queries = nullptr;
        Output* device_outputs = nullptr;
        check(cudaMalloc(&device_seed, sizeof(host_seed)), "cudaMalloc seed");
        check(cudaMalloc(&device_archive, sizeof(host_archive)), "cudaMalloc archive");
        check(cudaMalloc(&device_queries, host_queries.size() * sizeof(Query)), "cudaMalloc queries");
        check(cudaMalloc(&device_outputs, host_outputs.size() * sizeof(Output)), "cudaMalloc outputs");
        check(cudaMemcpy(device_seed, &host_seed, sizeof(host_seed), cudaMemcpyHostToDevice), "copy seed");
        check(cudaMemcpy(device_archive, &host_archive, sizeof(host_archive), cudaMemcpyHostToDevice), "copy archive");
        check(cudaMemcpy(device_queries, host_queries.data(), host_queries.size() * sizeof(Query), cudaMemcpyHostToDevice), "copy queries");

        constexpr std::uint32_t block = 256u;
        query_kernel<<<(kQueries + block - 1u) / block, block>>>(
            device_seed, 1u, device_archive, device_queries, device_outputs, kQueries);
        check(cudaGetLastError(), "query_kernel launch");
        check(cudaDeviceSynchronize(), "query_kernel synchronize");
        check(cudaMemcpy(host_outputs.data(), device_outputs,
                         host_outputs.size() * sizeof(Output), cudaMemcpyDeviceToHost),
              "copy outputs");

        for (std::uint32_t i = 0u; i < kQueries; ++i) {
            const auto cpu = tkm::state_at(
                &host_seed, 1u, host_archive, 0u, host_queries[i].seconds);
            const float difference = std::fabs(
                cpu.state.position.x - host_outputs[i].state.state.position.x);
            if (host_outputs[i].state.status != tkm::QueryStatus::Ok || difference > 1.0e-5f) {
                throw std::runtime_error("CPU/GPU state mismatch");
            }
        }

        cudaFree(device_outputs);
        cudaFree(device_queries);
        cudaFree(device_archive);
        cudaFree(device_seed);
        std::cout << "CUDA smoke test passed for " << kQueries << " queries.\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}

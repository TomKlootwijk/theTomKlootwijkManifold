#include "tkm/tkm.hpp"

#include <iomanip>
#include <iostream>

namespace {
using DemoArchive = tkm::Archive<4u, 4u>;

DemoArchive make_archive() {
    DemoArchive archive{};
    archive.segment_count = 2u;

    auto& first = archive.segments[0];
    first.begin_seconds = 0.0f;
    first.end_seconds = 10.0f;
    first.origin_seconds = 0.0f;
    first.flags = tkm::kSegmentActive;
    first.lineage_seed = 0x11111111u;

    auto& second = archive.segments[1];
    second.begin_seconds = 10.0f;
    second.end_seconds = 20.0f;
    second.origin_seconds = 10.0f;
    second.flags = tkm::kSegmentActive;
    second.lineage_seed = 0x22222222u;
    second.patches[0].object_index = 0u;
    second.patches[0].flags = tkm::kPatchActive | tkm::kPatchModeOverride;
    second.patches[0].mode_override = 2u;
    second.patches[0].lineage_tag = 0xabcdu;
    second.patches[0].delta_position0 = {0.0f, 1.0f, 0.0f};
    second.patches[0].delta_velocity = {0.0f, 0.1f, 0.0f};
    second.patches[0].delta_phase0 = 0.25f;
    return archive;
}
}

int main() {
    const tkm::Seed seeds[2] = {
        {{0.0f, 0.0f, 0.0f}, 0.0f,
         {1.0f, 0.0f, 0.0f}, 0.1f,
         {0.0f, 0.0f, 0.0f}, 0.0f,
         1u, 0x12345678u, 0u, 0u},
        {{0.0f, 2.0f, 0.0f}, 0.5f,
         {0.0f, 0.0f, 1.0f}, -0.05f,
         {0.0f, 0.0f, 0.0f}, 0.0f,
         1u, 0x87654321u, 0u, 0u},
    };
    const DemoArchive archive = make_archive();
    const std::uint32_t validation = tkm::validate_archive(seeds, 2u, archive);
    if (validation != tkm::kValidationOk) {
        std::cerr << "archive validation failed: 0x" << std::hex << validation << '\n';
        return 1;
    }

    tkm::Guard guard{};
    guard.kind = tkm::GuardKind::PlaneSdf;
    guard.a = {1.0f, 0.0f, 0.0f};
    guard.b = -8.0f;
    guard.required_mode = tkm::kAnyMode;
    guard.numeric_error = 0.0f;
    guard.event_margin = 1.0e-5f;
    if (tkm::validate_guard(guard) != tkm::kGuardValidationOk) {
        std::cerr << "guard validation failed\n";
        return 1;
    }

    std::cout << "Tom Klootwijk bounded-query substrate demo\n";
    std::cout << "carrier: R^3 x S^1, fixed profile: 4 segments x 4 patch slots\n\n";
    for (float time : {5.0f, 9.0f, 11.0f, 15.0f}) {
        const tkm::QueryResult query = tkm::state_at(seeds, 2u, archive, 0u, time);
        const tkm::GuardEvaluation evaluation = tkm::evaluate_guard(query.state, guard);
        std::cout << std::fixed << std::setprecision(4)
                  << "t=" << std::setw(6) << time
                  << " p=(" << query.state.position.x << ','
                  << query.state.position.y << ',' << query.state.position.z << ')'
                  << " phase=" << query.state.phase
                  << " mode=" << query.state.mode
                  << " segment=" << query.segment_index
                  << " patch_hits=" << query.patch_hits
                  << " guard=" << evaluation.value << '\n';
    }

    const auto before = tkm::state_at(seeds, 2u, archive, 0u, 7.0f);
    const auto after = tkm::state_at(seeds, 2u, archive, 0u, 9.0f);
    const auto event = tkm::classify_event(
        tkm::evaluate_guard(before.state, guard),
        tkm::evaluate_guard(after.state, guard),
        1u);
    std::cout << "\ncertified crossing: " << event.verified
              << " interpolation=" << event.interpolation << '\n';

    const auto bound = tkm::fixed_query_bound<4u, 4u>();
    std::cout << "fixed structural bound: segment tests=" << bound.segment_slot_tests
              << ", patch tests=" << bound.patch_slot_tests
              << ", seed evaluations=" << bound.seed_evaluations << '\n';
    return 0;
}

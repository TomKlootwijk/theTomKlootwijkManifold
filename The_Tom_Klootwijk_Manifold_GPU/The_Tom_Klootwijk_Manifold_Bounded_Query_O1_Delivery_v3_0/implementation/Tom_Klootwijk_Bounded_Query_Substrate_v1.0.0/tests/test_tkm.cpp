#include "tkm/tkm.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

bool near(float a, float b, float epsilon = 1.0e-5f) {
    return std::fabs(a - b) <= epsilon;
}

using TestArchive = tkm::Archive<8u, 8u>;

TestArchive make_archive() {
    TestArchive archive{};
    archive.segment_count = 3u;
    for (std::uint32_t i = 0u; i < 3u; ++i) {
        auto& segment = archive.segments[i];
        segment.begin_seconds = 10.0f * static_cast<float>(i);
        segment.end_seconds = 10.0f * static_cast<float>(i + 1u);
        segment.origin_seconds = segment.begin_seconds;
        segment.flags = tkm::kSegmentActive;
        segment.lineage_seed = 0x1000u + i;
    }
    auto& patch = archive.segments[1].patches[0];
    patch.object_index = 0u;
    patch.flags = tkm::kPatchActive | tkm::kPatchModeOverride;
    patch.mode_override = 7u;
    patch.lineage_tag = 0x55aau;
    patch.delta_position0 = {0.0f, 2.0f, 0.0f};
    patch.delta_velocity = {0.0f, 0.25f, 0.0f};
    patch.delta_phase0 = 0.3f;
    return archive;
}

void test_phase() {
    require(near(tkm::wrap_phase(0.0f), 0.0f), "phase zero");
    require(near(tkm::wrap_phase(tkm::kTwoPi + 0.25f), 0.25f), "phase positive wrap");
    require(near(tkm::wrap_phase(-tkm::kTwoPi - 0.25f), -0.25f), "phase negative wrap");
}

void test_state_and_patch() {
    const tkm::Seed seeds[1] = {
        {{1.0f, 2.0f, 3.0f}, 0.1f,
         {2.0f, 0.0f, -1.0f}, 0.2f,
         {0.5f, 0.0f, 0.0f}, 0.02f,
         3u, 0x1234u, 0u, 0u},
    };
    const TestArchive archive = make_archive();
    require(tkm::validate_archive(seeds, 1u, archive) == tkm::kValidationOk,
            "valid archive rejected");

    const auto a = tkm::state_at(seeds, 1u, archive, 0u, 5.0f);
    require(a.status == tkm::QueryStatus::Ok, "state query failed");
    require(a.segment_index == 0u, "wrong segment 0");
    require(a.patch_hits == 0u, "unexpected patch");
    require(near(a.state.position.x, 1.0f + 2.0f * 5.0f + 0.25f * 25.0f),
            "quadratic x predictor");
    require(a.state.mode == 3u, "base mode");

    const auto b = tkm::state_at(seeds, 1u, archive, 0u, 14.0f);
    require(b.status == tkm::QueryStatus::Ok, "patched state query failed");
    require(b.segment_index == 1u, "wrong segment 1");
    require(b.patch_hits == 1u, "patch not applied");
    const float expected_y = 2.0f + 2.0f + 0.25f * 4.0f;
    require(near(b.state.position.y, expected_y), "patch polynomial y");
    require(b.state.mode == 7u, "mode override");
}

void test_statuses() {
    const tkm::Seed seed{};
    TestArchive archive = make_archive();
    auto result = tkm::state_at(&seed, 1u, archive, 1u, 1.0f);
    require(result.status == tkm::QueryStatus::ObjectOutOfRange, "object range status");
    result = tkm::state_at(&seed, 1u, archive, 0u, 31.0f);
    require(result.status == tkm::QueryStatus::NoSegment, "no segment status");
    archive.magic = 0u;
    result = tkm::state_at(&seed, 1u, archive, 0u, 1.0f);
    require(result.status == tkm::QueryStatus::InvalidArchive, "invalid archive status");
}

void test_validation_rejects_ambiguity() {
    const tkm::Seed seed{};
    TestArchive archive = make_archive();
    archive.segments[1].patches[1] = archive.segments[1].patches[0];
    std::uint32_t bits = tkm::validate_archive(&seed, 1u, archive);
    require((bits & tkm::kDuplicatePatchObject) != 0u, "duplicate patch not rejected");

    archive = make_archive();
    archive.segments[1].begin_seconds = 9.0f;
    bits = tkm::validate_archive(&seed, 1u, archive);
    require((bits & tkm::kOverlappingSegments) != 0u, "overlap not rejected");
}

void test_exact_sdf_guards() {
    tkm::State state{};
    state.position = {3.0f, 0.0f, 0.0f};
    state.mode = 2u;

    tkm::Guard sphere{};
    sphere.kind = tkm::GuardKind::SphereSdf;
    sphere.a = {0.0f, 0.0f, 0.0f};
    sphere.b = 2.0f;
    sphere.required_mode = 2u;
    sphere.event_margin = 1.0e-4f;
    require(tkm::validate_guard(sphere) == tkm::kGuardValidationOk,
            "valid sphere guard rejected");
    const auto evaluation = tkm::evaluate_guard(state, sphere);
    require(near(evaluation.value, 1.0f), "sphere SDF");
    require(evaluation.supported == 1u && evaluation.compatible == 1u &&
            evaluation.certified == 1u, "guard gates");

    tkm::Guard plane{};
    plane.kind = tkm::GuardKind::PlaneSdf;
    plane.a = {1.0f, 0.0f, 0.0f};
    plane.b = 0.0f;
    plane.event_margin = 1.0e-4f;
    require(tkm::validate_guard(plane) == tkm::kGuardValidationOk,
            "valid plane guard rejected");
    tkm::Guard bad_plane = plane;
    bad_plane.a = {2.0f, 0.0f, 0.0f};
    require((tkm::validate_guard(bad_plane) & tkm::kGuardBadGeometry) != 0u,
            "non-unit plane SDF accepted");
    tkm::State before{};
    before.position = {1.0f, 0.0f, 0.0f};
    tkm::State after{};
    after.position = {-1.0f, 0.0f, 0.0f};
    const auto event = tkm::classify_event(
        tkm::evaluate_guard(before, plane),
        tkm::evaluate_guard(after, plane),
        1u);
    require(event.verified == 1u &&
            event.kind == tkm::EventKind::CrossingPositiveToNegative,
            "certified crossing");
    require(near(event.interpolation, 0.5f), "crossing interpolation");
    const auto no_interval_certificate = tkm::classify_event(
        tkm::evaluate_guard(before, plane),
        tkm::evaluate_guard(after, plane),
        0u);
    require(no_interval_certificate.verified == 0u,
            "crossing accepted without interval certificate");

    plane.numeric_error = 2.0f;
    const auto unresolved = tkm::classify_event(
        tkm::evaluate_guard(before, plane),
        tkm::evaluate_guard(after, plane),
        1u);
    require(unresolved.verified == 0u, "uncertified crossing accepted");
}

void test_random_reference() {
    const tkm::Seed seed{
        {1.0f, -2.0f, 0.5f}, 0.2f,
        {0.4f, -0.1f, 0.3f}, -0.05f,
        {0.02f, 0.03f, -0.01f}, 0.004f,
        4u, 0x9999u, 0u, 0u,
    };
    TestArchive archive = make_archive();
    auto& patch = archive.segments[2].patches[0];
    patch.object_index = 0u;
    patch.flags = tkm::kPatchActive;
    patch.delta_position0 = {0.2f, -0.3f, 0.1f};
    patch.delta_velocity = {0.01f, 0.02f, -0.01f};
    patch.delta_acceleration = {0.001f, 0.0f, 0.002f};
    patch.delta_phase0 = -0.2f;

    std::mt19937 rng(12345u);
    std::uniform_real_distribution<float> distribution(20.0f, 29.999f);
    for (int sample = 0; sample < 20000; ++sample) {
        const float t = distribution(rng);
        const float dt = t;
        const float local = t - 20.0f;
        const float half_dt2 = 0.5f * dt * dt;
        const float half_local2 = 0.5f * local * local;
        const tkm::Vec3 expected =
            seed.position0 + seed.velocity0 * dt + seed.acceleration0 * half_dt2 +
            patch.delta_position0 + patch.delta_velocity * local +
            patch.delta_acceleration * half_local2;
        const auto query = tkm::state_at(&seed, 1u, archive, 0u, t);
        require(query.status == tkm::QueryStatus::Ok, "random query status");
        require(near(query.state.position.x, expected.x, 2.0e-4f) &&
                near(query.state.position.y, expected.y, 2.0e-4f) &&
                near(query.state.position.z, expected.z, 2.0e-4f),
                "random reference mismatch");
    }
}

void test_complexity_and_little_o_ratio() {
    constexpr auto bound = tkm::fixed_query_bound<8u, 8u>(2u);
    static_assert(bound.segment_slot_tests == 8u);
    static_assert(bound.patch_slot_tests == 8u);
    static_assert(bound.seed_evaluations == 1u);
    static_assert(bound.guard_evaluations == 2u);

    const std::size_t bytes = 4096u;
    const double r1 = tkm::normalized_storage_ratio(bytes, 32u, 1024u);
    const double r2 = tkm::normalized_storage_ratio(bytes, 32u, 1024u * 1024u);
    require(r2 < r1 / 100.0, "normalized ratio did not decrease with dense sampling");
    const double scaled = r2 * static_cast<double>(1024u * 1024u);
    const double expected = static_cast<double>(bytes) /
        static_cast<double>(32u * sizeof(tkm::State));
    require(std::fabs(scaled - expected) < 1.0e-9, "ratio formula");
}

} // namespace

int main() {
    try {
        test_phase();
        test_state_and_patch();
        test_statuses();
        test_validation_rejects_ambiguity();
        test_exact_sdf_guards();
        test_random_reference();
        test_complexity_and_little_o_ratio();
        std::cout << "All TKM bounded-query tests passed.\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "TEST FAILURE: " << error.what() << '\n';
        return 1;
    }
}

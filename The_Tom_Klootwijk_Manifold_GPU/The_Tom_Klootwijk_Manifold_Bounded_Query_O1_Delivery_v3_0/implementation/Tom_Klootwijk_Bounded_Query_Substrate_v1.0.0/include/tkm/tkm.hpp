#pragma once

#include <cstddef>
#include <cstdint>
#include <cmath>
#include <limits>
#include <type_traits>

#ifdef __CUDACC__
#define TKM_HD __host__ __device__
#define TKM_INLINE __forceinline__
#else
#define TKM_HD
#if defined(_MSC_VER)
#define TKM_INLINE __forceinline
#else
#define TKM_INLINE inline __attribute__((always_inline))
#endif
#endif

namespace tkm {

constexpr float kPi = 3.14159265358979323846f;
constexpr float kTwoPi = 6.28318530717958647692f;
constexpr std::uint32_t kInvalidIndex = 0xffffffffu;
constexpr std::uint32_t kAnyMode = 0xffffffffu;
constexpr std::uint32_t kArchiveMagic = 0x544b4d31u; // "TKM1"

struct Vec3 {
    float x{};
    float y{};
    float z{};
};

TKM_HD TKM_INLINE Vec3 operator+(const Vec3& a, const Vec3& b) {
    return {a.x + b.x, a.y + b.y, a.z + b.z};
}

TKM_HD TKM_INLINE Vec3 operator-(const Vec3& a, const Vec3& b) {
    return {a.x - b.x, a.y - b.y, a.z - b.z};
}

TKM_HD TKM_INLINE Vec3 operator*(const Vec3& a, float s) {
    return {a.x * s, a.y * s, a.z * s};
}

TKM_HD TKM_INLINE float dot(const Vec3& a, const Vec3& b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

TKM_HD TKM_INLINE float length(const Vec3& v) {
    return ::sqrtf(dot(v, v));
}

TKM_HD TKM_INLINE float wrap_phase(float value) {
    const float turns = ::floorf((value + kPi) / kTwoPi);
    return value - turns * kTwoPi;
}

TKM_HD TKM_INLINE std::uint32_t mix32(std::uint32_t x) {
    x ^= x >> 16u;
    x *= 0x7feb352du;
    x ^= x >> 15u;
    x *= 0x846ca68bu;
    x ^= x >> 16u;
    return x;
}

// Continuous carrier used by the reference implementation:
// M = R^3 x S^1. A finite mode label selects a disconnected copy of M.
struct alignas(16) State {
    Vec3 position{};
    float phase{};
    std::uint32_t mode{};
    std::uint32_t lineage{};
    std::uint32_t reserved0{};
    std::uint32_t reserved1{};
};

// Fixed-size closed-form seed. The reference predictor is a quadratic jet in
// R^3 and S^1. It is a model contract, not an arbitrary physics solver.
struct alignas(16) Seed {
    Vec3 position0{};
    float phase0{};
    Vec3 velocity0{};
    float phase_velocity{};
    Vec3 acceleration0{};
    float phase_acceleration{};
    std::uint32_t mode{};
    std::uint32_t lineage_seed{};
    std::uint32_t reserved0{};
    std::uint32_t reserved1{};
};

constexpr std::uint32_t kPatchActive = 1u << 0u;
constexpr std::uint32_t kPatchModeOverride = 1u << 1u;

// A cumulative chart-local correction valid on one segment. Fixed polynomial
// degree keeps evaluation work bounded. Topology/mode changes are explicit.
struct alignas(16) Patch {
    std::uint32_t object_index{kInvalidIndex};
    std::uint32_t flags{};
    std::uint32_t mode_override{};
    std::uint32_t lineage_tag{};

    Vec3 delta_position0{};
    float delta_phase0{};
    Vec3 delta_velocity{};
    float delta_phase_velocity{};
    Vec3 delta_acceleration{};
    float delta_phase_acceleration{};
};

constexpr std::uint32_t kSegmentActive = 1u << 0u;

// Segment intervals are half-open [begin, end). The archive profile fixes the
// maximum segment and patch counts at compile time.
template <std::size_t MaxPatches>
struct alignas(16) Segment {
    float begin_seconds{};
    float end_seconds{};
    float origin_seconds{};
    std::uint32_t flags{};
    std::uint32_t lineage_seed{};
    std::uint32_t reserved0{};
    std::uint32_t reserved1{};
    std::uint32_t reserved2{};
    Patch patches[MaxPatches]{};
};

template <std::size_t MaxSegments, std::size_t MaxPatches>
struct alignas(16) Archive {
    std::uint32_t magic{kArchiveMagic};
    std::uint32_t version{1u};
    std::uint32_t segment_count{};
    std::uint32_t flags{};
    Segment<MaxPatches> segments[MaxSegments]{};
};

enum class QueryStatus : std::uint32_t {
    Ok = 0u,
    ObjectOutOfRange = 1u,
    NoSegment = 2u,
    InvalidArchive = 3u,
};

struct alignas(16) QueryResult {
    State state{};
    QueryStatus status{QueryStatus::InvalidArchive};
    std::uint32_t segment_index{kInvalidIndex};
    std::uint32_t patch_hits{};
    std::uint32_t reserved{};
};

struct PatchValue {
    Vec3 delta_position{};
    float delta_phase{};
    std::uint32_t mode_override{};
    std::uint32_t has_mode_override{};
    std::uint32_t lineage_tag{};
    std::uint32_t hit_count{};
};

TKM_HD TKM_INLINE State predict_seed(const Seed& seed, float seconds) {
    const float dt = seconds;
    const float half_dt2 = 0.5f * dt * dt;
    const Vec3 position = seed.position0 + seed.velocity0 * dt + seed.acceleration0 * half_dt2;
    const float phase = wrap_phase(
        seed.phase0 + seed.phase_velocity * dt + seed.phase_acceleration * half_dt2);
    return {position, phase, seed.mode, seed.lineage_seed, 0u, 0u};
}

template <std::size_t MaxSegments, std::size_t MaxPatches>
TKM_HD TKM_INLINE std::uint32_t select_segment(
    const Archive<MaxSegments, MaxPatches>& archive,
    float seconds) {
    std::uint32_t selected = kInvalidIndex;
    // Deliberately scan the complete compile-time profile. This is a fixed
    // upper bound independent of represented sample count or history length.
    for (std::size_t index = 0u; index < MaxSegments; ++index) {
        const bool in_declared_count = index < static_cast<std::size_t>(archive.segment_count);
        const Segment<MaxPatches>& segment = archive.segments[index];
        const bool active = (segment.flags & kSegmentActive) != 0u;
        const bool contains = seconds >= segment.begin_seconds && seconds < segment.end_seconds;
        if (selected == kInvalidIndex && in_declared_count && active && contains) {
            selected = static_cast<std::uint32_t>(index);
        }
    }
    return selected;
}

template <std::size_t MaxPatches>
TKM_HD TKM_INLINE PatchValue evaluate_patch_slots(
    const Segment<MaxPatches>& segment,
    std::uint32_t object_index,
    float seconds) {
    PatchValue value{};
    const float dt = seconds - segment.origin_seconds;
    const float half_dt2 = 0.5f * dt * dt;
    // The complete fixed slot array is inspected. A valid archive has at most
    // one active slot per object per segment; validation rejects duplicates.
    for (std::size_t slot = 0u; slot < MaxPatches; ++slot) {
        const Patch& patch = segment.patches[slot];
        const bool matches = (patch.flags & kPatchActive) != 0u &&
                             patch.object_index == object_index;
        if (matches) {
            value.delta_position = value.delta_position +
                patch.delta_position0 + patch.delta_velocity * dt +
                patch.delta_acceleration * half_dt2;
            value.delta_phase += patch.delta_phase0 +
                patch.delta_phase_velocity * dt +
                patch.delta_phase_acceleration * half_dt2;
            if ((patch.flags & kPatchModeOverride) != 0u) {
                value.mode_override = patch.mode_override;
                value.has_mode_override = 1u;
            }
            value.lineage_tag ^= patch.lineage_tag;
            ++value.hit_count;
        }
    }
    return value;
}

template <std::size_t MaxSegments, std::size_t MaxPatches>
TKM_HD TKM_INLINE QueryResult state_at(
    const Seed* seeds,
    std::uint32_t seed_count,
    const Archive<MaxSegments, MaxPatches>& archive,
    std::uint32_t object_index,
    float seconds) {
    QueryResult result{};
    if (archive.magic != kArchiveMagic || archive.version != 1u ||
        archive.segment_count > MaxSegments) {
        result.status = QueryStatus::InvalidArchive;
        return result;
    }
    if (object_index >= seed_count) {
        result.status = QueryStatus::ObjectOutOfRange;
        return result;
    }
    const std::uint32_t segment_index = select_segment(archive, seconds);
    if (segment_index == kInvalidIndex) {
        result.status = QueryStatus::NoSegment;
        return result;
    }

    const Seed& seed = seeds[object_index];
    const Segment<MaxPatches>& segment = archive.segments[segment_index];
    State state = predict_seed(seed, seconds);
    const PatchValue patch = evaluate_patch_slots(segment, object_index, seconds);

    // Retraction for R^3 x S^1: vector addition in R^3 and addition modulo 2pi
    // in the circle coordinate. This is chart-local and exact for this carrier.
    state.position = state.position + patch.delta_position;
    state.phase = wrap_phase(state.phase + patch.delta_phase);
    if (patch.has_mode_override != 0u) {
        state.mode = patch.mode_override;
    }
    state.lineage = mix32(
        seed.lineage_seed ^ segment.lineage_seed ^ patch.lineage_tag ^
        object_index ^ (state.mode * 0x9e3779b9u));

    result.state = state;
    result.status = QueryStatus::Ok;
    result.segment_index = segment_index;
    result.patch_hits = patch.hit_count;
    return result;
}

enum class GuardKind : std::uint32_t {
    SphereSdf = 1u,
    PlaneSdf = 2u,
};

struct alignas(16) Guard {
    GuardKind kind{GuardKind::SphereSdf};
    std::uint32_t required_mode{kAnyMode};
    float numeric_error{};
    float event_margin{};

    // Sphere: a=center, b=radius. Plane: a=unit normal, b=offset in dot(a,p)+b.
    Vec3 a{};
    float b{};

    // support_radius < 0 means globally supported.
    Vec3 support_center{};
    float support_radius{-1.0f};
};

enum GuardValidationBits : std::uint32_t {
    kGuardValidationOk = 0u,
    kGuardBadKind = 1u << 0u,
    kGuardBadGeometry = 1u << 1u,
    kGuardBadErrorContract = 1u << 2u,
    kGuardBadSupport = 1u << 3u,
};

inline std::uint32_t validate_guard(const Guard& guard, float unit_tolerance = 1.0e-4f) {
    std::uint32_t bits = kGuardValidationOk;
    const auto kind = static_cast<std::uint32_t>(guard.kind);
    if (kind != static_cast<std::uint32_t>(GuardKind::SphereSdf) &&
        kind != static_cast<std::uint32_t>(GuardKind::PlaneSdf)) {
        bits |= kGuardBadKind;
    }
    const bool a_finite = std::isfinite(guard.a.x) && std::isfinite(guard.a.y) &&
        std::isfinite(guard.a.z);
    if (!a_finite || !std::isfinite(guard.b)) {
        bits |= kGuardBadGeometry;
    } else if (guard.kind == GuardKind::SphereSdf) {
        if (!(guard.b > 0.0f)) bits |= kGuardBadGeometry;
    } else if (guard.kind == GuardKind::PlaneSdf) {
        const float normal_length = std::sqrt(dot(guard.a, guard.a));
        if (!std::isfinite(normal_length) ||
            std::fabs(normal_length - 1.0f) > unit_tolerance) {
            bits |= kGuardBadGeometry;
        }
    }
    if (!std::isfinite(guard.numeric_error) || !std::isfinite(guard.event_margin) ||
        guard.numeric_error < 0.0f || guard.event_margin < 0.0f) {
        bits |= kGuardBadErrorContract;
    }
    const bool support_finite = std::isfinite(guard.support_center.x) &&
        std::isfinite(guard.support_center.y) && std::isfinite(guard.support_center.z);
    if (!support_finite || !std::isfinite(guard.support_radius)) {
        bits |= kGuardBadSupport;
    }
    return bits;
}

struct alignas(16) GuardEvaluation {
    float value{};
    float error{};
    std::uint32_t supported{};
    std::uint32_t compatible{};
    std::uint32_t certified{};
    std::uint32_t reserved0{};
    std::uint32_t reserved1{};
    std::uint32_t reserved2{};
};

TKM_HD TKM_INLINE GuardEvaluation evaluate_guard(const State& state, const Guard& guard) {
    float value = 0.0f;
    if (guard.kind == GuardKind::SphereSdf) {
        value = length(state.position - guard.a) - guard.b;
    } else {
        value = dot(guard.a, state.position) + guard.b;
    }
    const bool supported = guard.support_radius < 0.0f ||
        length(state.position - guard.support_center) <= guard.support_radius;
    const bool compatible = guard.required_mode == kAnyMode ||
        guard.required_mode == state.mode;
    const bool certified = guard.numeric_error <= guard.event_margin;
    return {
        value,
        guard.numeric_error,
        supported ? 1u : 0u,
        compatible ? 1u : 0u,
        certified ? 1u : 0u,
        0u, 0u, 0u,
    };
}

enum class EventKind : std::uint32_t {
    None = 0u,
    CrossingPositiveToNegative = 1u,
    CrossingNegativeToPositive = 2u,
    UnresolvedTouch = 3u,
};

struct alignas(16) EventResult {
    EventKind kind{EventKind::None};
    std::uint32_t verified{};
    float interpolation{};
    float minimum_interval_distance{};
};

TKM_HD TKM_INLINE EventResult classify_event(
    const GuardEvaluation& before,
    const GuardEvaluation& after,
    std::uint32_t interval_certificate) {
    const float before_low = before.value - before.error;
    const float before_high = before.value + before.error;
    const float after_low = after.value - after.error;
    const float after_high = after.value + after.error;

    // Endpoint sign separation implies an actual zero crossing only when the
    // caller certifies continuity of guard(state(t)) and validity of support/
    // compatibility over the whole interval (not merely at its endpoints).
    const bool gates = interval_certificate != 0u &&
        before.supported != 0u && after.supported != 0u &&
        before.compatible != 0u && after.compatible != 0u &&
        before.certified != 0u && after.certified != 0u;
    const bool positive_to_negative = before_low > 0.0f && after_high < 0.0f;
    const bool negative_to_positive = before_high < 0.0f && after_low > 0.0f;

    float denominator = before.value - after.value;
    float interpolation = ::fabsf(denominator) > 1.0e-20f
        ? before.value / denominator
        : 0.5f;
    interpolation = interpolation < 0.0f ? 0.0f :
        (interpolation > 1.0f ? 1.0f : interpolation);

    if (gates && positive_to_negative) {
        return {EventKind::CrossingPositiveToNegative, 1u, interpolation, 0.0f};
    }
    if (gates && negative_to_positive) {
        return {EventKind::CrossingNegativeToPositive, 1u, interpolation, 0.0f};
    }

    const float before_distance = before_low > 0.0f ? before_low :
        (before_high < 0.0f ? -before_high : 0.0f);
    const float after_distance = after_low > 0.0f ? after_low :
        (after_high < 0.0f ? -after_high : 0.0f);
    const float minimum_distance = before_distance < after_distance
        ? before_distance : after_distance;
    const bool touches_interval = before_distance == 0.0f || after_distance == 0.0f;
    if (gates && touches_interval) {
        return {EventKind::UnresolvedTouch, 0u, interpolation, minimum_distance};
    }
    return {EventKind::None, 0u, interpolation, minimum_distance};
}

struct QueryComplexityBound {
    std::size_t segment_slot_tests{};
    std::size_t patch_slot_tests{};
    std::size_t seed_evaluations{};
    std::size_t guard_evaluations{};
};

template <std::size_t MaxSegments, std::size_t MaxPatches>
constexpr QueryComplexityBound fixed_query_bound(std::size_t guards = 1u) {
    return {MaxSegments, MaxPatches, 1u, guards};
}

enum ValidationBits : std::uint32_t {
    kValidationOk = 0u,
    kBadMagic = 1u << 0u,
    kBadVersion = 1u << 1u,
    kTooManySegments = 1u << 2u,
    kBadSegmentInterval = 1u << 3u,
    kOverlappingSegments = 1u << 4u,
    kBadPatchObject = 1u << 5u,
    kDuplicatePatchObject = 1u << 6u,
    kNonFiniteValue = 1u << 7u,
    kBadSeed = 1u << 8u,
};

inline bool finite_vec3(const Vec3& value) {
    return std::isfinite(value.x) && std::isfinite(value.y) && std::isfinite(value.z);
}

template <std::size_t MaxSegments, std::size_t MaxPatches>
std::uint32_t validate_archive(
    const Seed* seeds,
    std::uint32_t seed_count,
    const Archive<MaxSegments, MaxPatches>& archive) {
    std::uint32_t bits = kValidationOk;
    if (archive.magic != kArchiveMagic) bits |= kBadMagic;
    if (archive.version != 1u) bits |= kBadVersion;
    if (archive.segment_count > MaxSegments) bits |= kTooManySegments;
    for (std::uint32_t i = 0u; i < seed_count; ++i) {
        const Seed& seed = seeds[i];
        if (!finite_vec3(seed.position0) || !finite_vec3(seed.velocity0) ||
            !finite_vec3(seed.acceleration0) || !std::isfinite(seed.phase0) ||
            !std::isfinite(seed.phase_velocity) || !std::isfinite(seed.phase_acceleration)) {
            bits |= kBadSeed;
        }
    }
    const std::size_t count = archive.segment_count < MaxSegments
        ? archive.segment_count : MaxSegments;
    for (std::size_t i = 0u; i < count; ++i) {
        const Segment<MaxPatches>& segment = archive.segments[i];
        if (!std::isfinite(segment.begin_seconds) || !std::isfinite(segment.end_seconds) ||
            !std::isfinite(segment.origin_seconds) ||
            !(segment.begin_seconds < segment.end_seconds)) {
            bits |= kBadSegmentInterval;
        }
        if (i > 0u && segment.begin_seconds < archive.segments[i - 1u].end_seconds) {
            bits |= kOverlappingSegments;
        }
        for (std::size_t p = 0u; p < MaxPatches; ++p) {
            const Patch& patch = segment.patches[p];
            if ((patch.flags & kPatchActive) == 0u) continue;
            if (patch.object_index >= seed_count) bits |= kBadPatchObject;
            if (!finite_vec3(patch.delta_position0) || !finite_vec3(patch.delta_velocity) ||
                !finite_vec3(patch.delta_acceleration) ||
                !std::isfinite(patch.delta_phase0) ||
                !std::isfinite(patch.delta_phase_velocity) ||
                !std::isfinite(patch.delta_phase_acceleration)) {
                bits |= kNonFiniteValue;
            }
            for (std::size_t q = p + 1u; q < MaxPatches; ++q) {
                const Patch& other = segment.patches[q];
                if ((other.flags & kPatchActive) != 0u &&
                    other.object_index == patch.object_index) {
                    bits |= kDuplicatePatchObject;
                }
            }
        }
    }
    return bits;
}

inline double normalized_storage_ratio(
    std::size_t encoded_bytes,
    std::size_t entity_count,
    std::size_t dense_sample_count,
    std::size_t dense_state_bytes = sizeof(State)) {
    if (entity_count == 0u || dense_sample_count == 0u || dense_state_bytes == 0u) {
        return std::numeric_limits<double>::infinity();
    }
    const long double dense_bytes = static_cast<long double>(entity_count) *
        static_cast<long double>(dense_sample_count) *
        static_cast<long double>(dense_state_bytes);
    return static_cast<double>(static_cast<long double>(encoded_bytes) / dense_bytes);
}

static_assert(std::is_trivially_copyable_v<Vec3>);
static_assert(std::is_trivially_copyable_v<State>);
static_assert(std::is_trivially_copyable_v<Seed>);
static_assert(std::is_trivially_copyable_v<Patch>);
static_assert(sizeof(Seed) == 64u, "Seed ABI must remain 64 bytes");
static_assert(sizeof(Patch) == 64u, "Patch ABI must remain 64 bytes");

} // namespace tkm

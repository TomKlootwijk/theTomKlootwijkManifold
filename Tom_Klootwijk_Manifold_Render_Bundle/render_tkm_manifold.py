#!/usr/bin/env python3
"""Numerical renderer for a conforming Tom Klootwijk Manifold (TKM 1.0) instance.

This is not an AI image generator. It constructs an explicit typed implicit field on
X7 = R^3_position x R_time x S1_phase x R_route_lift x R_profile,
extracts a visible three-dimensional position slice of B_TK = f^{-1}(0), validates
that slice, and renders it with ordinary numerical geometry/rasterization.

The full TKM boundary is six-dimensional; the output is a declared 3D position slice
with four hidden coordinates fixed (or varied in the animation).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

import numpy as np

# Use a headless backend before importing pyplot.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.animation import FFMpegWriter
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

try:
    import plotly.graph_objects as go
    import plotly.io as pio
except Exception:  # pragma: no cover - optional output
    go = None
    pio = None

try:
    import trimesh
except Exception:  # pragma: no cover - optional output
    trimesh = None


TAU = 2.0 * math.pi

# Visual palette for the technical render (not generative imagery).
BG = np.array([0.018, 0.028, 0.050])
SURFACE_A = np.array([0.060, 0.500, 0.680])
SURFACE_B = np.array([0.300, 0.900, 0.800])
ACCENT = np.array([0.970, 0.690, 0.220])
TEXT = np.array([0.920, 0.945, 0.970])
MUTED = np.array([0.560, 0.640, 0.720])
PATH_COLOR = np.array([0.980, 0.985, 0.990])
EVENT_COLOR = np.array([0.990, 0.350, 0.250])


@dataclass(frozen=True)
class HiddenState:
    time: float
    phase: float
    route_lift: float
    profile: float


@dataclass(frozen=True)
class RenderConfig:
    address_decimal: int = 943
    address_width: int = 7
    amplitude_axes: float = 1.50
    amplitude_ternary: float = 0.18
    amplitude_vertical: float = 0.07
    theta_samples_still: int = 181
    phi_samples_still: int = 360
    theta_samples_animation: int = 49
    phi_samples_animation: int = 96
    animation_frames: int = 48
    animation_fps: int = 16
    event_tolerance: float = 1.0e-9


def base_digits(number: int, base: int, width: int) -> np.ndarray:
    if number < 0:
        raise ValueError("number must be non-negative")
    if base < 2:
        raise ValueError("base must be >= 2")
    digits: list[int] = []
    n = number
    if n == 0:
        digits = [0]
    while n:
        digits.append(n % base)
        n //= base
    digits = list(reversed(digits))
    if len(digits) > width:
        raise ValueError(f"{number} requires more than {width} base-{base} digits")
    return np.array([0] * (width - len(digits)) + digits, dtype=float)


def projection_matrix() -> np.ndarray:
    """Return a 3x7 orthonormal-row Fourier projection of the R^7 basis."""
    j = np.arange(7, dtype=float)
    scale = math.sqrt(2.0 / 7.0)
    p = np.vstack(
        [
            scale * np.cos(TAU * j / 7.0),
            scale * np.sin(TAU * j / 7.0),
            scale * np.cos(2.0 * TAU * j / 7.0),
        ]
    )
    return p


def projected_axes() -> tuple[np.ndarray, np.ndarray]:
    p = projection_matrix()
    d = (p / np.linalg.norm(p, axis=0, keepdims=True)).T
    return p, d


P_MATRIX, AXES = projected_axes()
J = np.arange(7, dtype=float)


def canonical_hidden_state() -> HiddenState:
    return HiddenState(time=0.0, phase=0.40, route_lift=-0.60, profile=0.50)


def hidden_state_at(tau: float) -> HiddenState:
    """A bounded, deterministic continuous flow for animation."""
    return HiddenState(
        time=tau,
        phase=0.40 + 0.42 * math.sin(tau),
        route_lift=-0.60 + 0.28 * math.cos(0.70 * tau),
        profile=0.55 * math.sin(0.50 * tau),
    )


def address_weights(address_digits: np.ndarray, hidden: HiddenState) -> np.ndarray:
    """Positive axis weights selected by a bounded ternary address record."""
    if address_digits.shape != (7,):
        raise ValueError("address_digits must contain exactly seven symbols")
    if np.any((address_digits < 0) | (address_digits > 2)):
        raise ValueError("canonical TKM render address uses ternary symbols 0,1,2")
    gain = 0.48 + 0.34 * address_digits  # 0.48, 0.82, 1.16
    oscillation = (
        1.0
        + 0.15 * np.cos(TAU * J / 7.0 + hidden.phase + 0.55 * hidden.time)
        + 0.06 * np.sin(2.0 * TAU * J / 7.0 + hidden.route_lift - 0.35 * hidden.time)
        + 0.03 * hidden.profile * np.cos(3.0 * TAU * J / 7.0 + 0.80 * hidden.time)
    )
    return gain * oscillation


def radius_on_sphere(
    n: np.ndarray,
    hidden: HiddenState,
    address_digits: np.ndarray,
    config: RenderConfig,
) -> np.ndarray:
    """Positive smooth radial graph defining the visible zero-level slice.

    n has shape (..., 3) and is assumed to be unit length.  The seven projected
    R^7 axes create smooth axis lobes.  A finite depth-3 ternary harmonic grammar
    contributes degrees 3, 9 and 27; it is bounded and is not claimed to be an
    infinite fractal.
    """
    n = np.asarray(n, dtype=float)
    dots = np.tensordot(n, AXES.T, axes=([-1], [0]))  # (..., 7)

    # E[(n dot d)^12] = 1/13 for a uniform n on S^2.  This basis term has zero mean.
    axis_basis = (13.0 * dots**12 - 1.0) / 12.0
    weights = address_weights(address_digits, hidden)
    axis_term = np.mean(axis_basis * weights, axis=-1)

    zeta = n[..., 0] + 1j * n[..., 1]
    ternary_term = (
        0.72 * np.real(zeta**3 * np.exp(1j * (hidden.phase + 0.30 * hidden.time)))
        + 0.20 * np.real(zeta**9 * np.exp(1j * (hidden.route_lift - 0.50 * hidden.time)))
        + 0.08 * np.real(zeta**27 * np.exp(1j * (hidden.profile + 0.20 * hidden.time)))
    )
    vertical_term = (1.0 - n[..., 2] ** 2) * np.sin(
        4.0 * n[..., 2] + hidden.route_lift + 0.25 * hidden.time
    )

    return (
        1.0
        + config.amplitude_axes * axis_term
        + config.amplitude_ternary * ternary_term
        + config.amplitude_vertical * vertical_term
    )


def field_value(
    points: np.ndarray,
    hidden: HiddenState,
    address_digits: np.ndarray,
    config: RenderConfig,
) -> np.ndarray:
    """Typed generic implicit field f(p,h) = ||p|| - R(p/||p||,h)."""
    p = np.asarray(points, dtype=float)
    r = np.linalg.norm(p, axis=-1)
    if np.any(r <= 0.0):
        raise ValueError("field domain excludes p=0; the zero set has radius > 0")
    n = p / r[..., None]
    return r - radius_on_sphere(n, hidden, address_digits, config)


def uv_sphere_mesh(
    n_theta: int,
    n_phi: int,
    hidden: HiddenState,
    address_digits: np.ndarray,
    config: RenderConfig,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Create a watertight oriented triangular mesh of the radial zero set."""
    if n_theta < 4 or n_phi < 8:
        raise ValueError("mesh resolution is too small")

    vertices_n: list[np.ndarray] = [np.array([0.0, 0.0, 1.0])]
    for ti in range(1, n_theta - 1):
        theta = math.pi * ti / (n_theta - 1)
        s, c = math.sin(theta), math.cos(theta)
        phi = TAU * np.arange(n_phi) / n_phi
        ring = np.column_stack((s * np.cos(phi), s * np.sin(phi), np.full(n_phi, c)))
        vertices_n.extend(ring)
    vertices_n.append(np.array([0.0, 0.0, -1.0]))
    normals_param = np.asarray(vertices_n, dtype=float)

    radii = radius_on_sphere(normals_param, hidden, address_digits, config)
    vertices = normals_param * radii[:, None]

    north = 0
    south = len(vertices) - 1
    ring_count = n_theta - 2

    def idx(ring: int, phi_idx: int) -> int:
        return 1 + ring * n_phi + (phi_idx % n_phi)

    faces: list[tuple[int, int, int]] = []
    # Top fan, oriented outward.
    for k in range(n_phi):
        faces.append((north, idx(0, k), idx(0, k + 1)))
    # Middle bands.
    for r in range(ring_count - 1):
        for k in range(n_phi):
            a = idx(r, k)
            b = idx(r, k + 1)
            c = idx(r + 1, k)
            d = idx(r + 1, k + 1)
            faces.append((a, c, b))
            faces.append((b, c, d))
    # Bottom fan.
    last = ring_count - 1
    for k in range(n_phi):
        faces.append((south, idx(last, k + 1), idx(last, k)))

    return vertices, np.asarray(faces, dtype=np.int64), radii, normals_param


def route_directions(parameters: np.ndarray) -> np.ndarray:
    """Unit route with two certified crossings and three tangencies of n_z=0."""
    s = np.asarray(parameters, dtype=float)
    return np.column_stack(
        (
            np.cos(s),
            np.sin(s) * np.cos(2.0 * s),
            np.sin(s) * np.sin(2.0 * s),
        )
    )


def surface_route(
    hidden: HiddenState,
    address_digits: np.ndarray,
    config: RenderConfig,
    samples: int = 601,
) -> tuple[np.ndarray, np.ndarray]:
    s = np.linspace(0.0, TAU, samples)
    n = route_directions(s)
    r = radius_on_sphere(n, hidden, address_digits, config)
    return s, n * r[:, None]


def guard_ring(
    hidden: HiddenState,
    address_digits: np.ndarray,
    config: RenderConfig,
    samples: int = 401,
) -> np.ndarray:
    a = np.linspace(0.0, TAU, samples)
    n = np.column_stack((np.cos(a), np.sin(a), np.zeros_like(a)))
    r = radius_on_sphere(n, hidden, address_digits, config)
    return n * r[:, None]


def verified_event_points(
    hidden: HiddenState,
    address_digits: np.ndarray,
    config: RenderConfig,
) -> tuple[np.ndarray, list[dict[str, float | str]]]:
    # For n_z(s)=sin(s)sin(2s), pi/2 and 3pi/2 are non-degenerate sign crossings.
    crossing_parameters = np.array([0.5 * math.pi, 1.5 * math.pi])
    n = route_directions(crossing_parameters)
    r = radius_on_sphere(n, hidden, address_digits, config)
    points = n * r[:, None]
    events = []
    for k, (s, p) in enumerate(zip(crossing_parameters, points, strict=True), start=1):
        events.append(
            {
                "event_id": f"crossing-{k}",
                "route_parameter": float(s),
                "guard": "n_z=0",
                "classification": "crossing",
                "support": "accepted",
                "compatibility": "accepted",
                "residual": float(abs(p[2])),
            }
        )
    return points, events


def camera_vector(elev_deg: float, azim_deg: float) -> np.ndarray:
    e = math.radians(elev_deg)
    a = math.radians(azim_deg)
    return np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])


def face_geometry(vertices: np.ndarray, faces: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    tri = vertices[faces]
    raw = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    norm = np.linalg.norm(raw, axis=1)
    normals = raw / np.maximum(norm[:, None], 1.0e-15)
    centers = tri.mean(axis=1)
    return normals, centers


def face_colors(
    vertices: np.ndarray,
    faces: np.ndarray,
    vertex_radii: np.ndarray,
    elev_deg: float,
    azim_deg: float,
) -> np.ndarray:
    normals, centers = face_geometry(vertices, faces)
    light = np.array([-0.35, -0.20, 0.92])
    light /= np.linalg.norm(light)
    view = camera_vector(elev_deg, azim_deg)
    diffuse = np.clip(normals @ light, 0.0, 1.0)
    rim = np.clip(1.0 - np.abs(normals @ view), 0.0, 1.0) ** 1.7

    face_r = vertex_radii[faces].mean(axis=1)
    lo, hi = np.percentile(face_r, [2.0, 98.0])
    scalar = np.clip((face_r - lo) / max(hi - lo, 1.0e-12), 0.0, 1.0)
    base = SURFACE_A[None, :] * (1.0 - scalar[:, None]) + SURFACE_B[None, :] * scalar[:, None]
    shade = (0.42 + 0.58 * diffuse)[:, None]
    rgb = base * shade + 0.20 * rim[:, None] * ACCENT[None, :]
    return np.clip(rgb, 0.0, 1.0)


def setup_3d_axis(fig: plt.Figure, elev: float, azim: float, limit: float = 1.52):
    ax = fig.add_subplot(111, projection="3d", computed_zorder=False)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_axis_off()
    ax.set_box_aspect((1.0, 1.0, 1.0), zoom=1.24)
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    ax.set_zlim(-limit, limit)
    ax.view_init(elev=elev, azim=azim)
    return ax


def add_axis_guides(ax, limit: float = 1.45) -> list:
    artists = []
    for k, direction in enumerate(AXES):
        t = np.array([-limit, limit])
        # Slightly varied intensity makes overlapping projected lines readable.
        color = ACCENT * (0.65 + 0.05 * k)
        artist, = ax.plot(
            t * direction[0],
            t * direction[1],
            t * direction[2],
            color=np.clip(color, 0.0, 1.0),
            linewidth=1.15,
            alpha=0.62,
            zorder=4,
        )
        artists.append(artist)
    return artists


def add_context_artists(ax, hidden: HiddenState, address: np.ndarray, config: RenderConfig):
    s, route = surface_route(hidden, address, config)
    ring = guard_ring(hidden, address, config)
    events, event_records = verified_event_points(hidden, address, config)
    route_draw = route * 1.018
    ring_draw = ring * 1.014
    events_draw = events * 1.024
    route_line, = ax.plot(route_draw[:, 0], route_draw[:, 1], route_draw[:, 2], color=PATH_COLOR, linewidth=2.05, alpha=0.98, zorder=12)
    guard_line, = ax.plot(
        ring_draw[:, 0], ring_draw[:, 1], ring_draw[:, 2], color=ACCENT, linewidth=1.55, linestyle="--", alpha=0.98, zorder=11
    )
    event_scatter = ax.scatter(
        events_draw[:, 0], events_draw[:, 1], events_draw[:, 2], s=54, c=[EVENT_COLOR], depthshade=False, edgecolors="none", zorder=13
    )
    return route_line, guard_line, event_scatter, event_records


def render_still(
    output: Path,
    hidden: HiddenState,
    address: np.ndarray,
    config: RenderConfig,
) -> dict:
    vertices, faces, radii, _ = uv_sphere_mesh(
        config.theta_samples_still,
        config.phi_samples_still,
        hidden,
        address,
        config,
    )
    elev, azim = 25.0, 42.0
    colors = face_colors(vertices, faces, radii, elev, azim)

    fig = plt.figure(figsize=(12.0, 8.0), dpi=180)
    ax = setup_3d_axis(fig, elev, azim)
    triangles = vertices[faces]
    poly = Poly3DCollection(triangles, facecolors=colors, edgecolors="none", linewidths=0.0, antialiased=True, zorder=2)
    poly.set_zsort("average")
    ax.add_collection3d(poly)
    add_axis_guides(ax)
    _, _, _, event_records = add_context_artists(ax, hidden, address, config)

    address_text = "".join(str(int(x)) for x in address)
    fig.text(
        0.055,
        0.935,
        "TOM KLOOTWIJK MANIFOLD - NUMERICAL ZERO-LEVEL RENDER",
        color=TEXT,
        fontsize=15.5,
        fontweight="bold",
        ha="left",
    )
    fig.text(
        0.055,
        0.895,
        r"Visible position slice of $B_{TK}=f^{-1}(0)$; the full regular boundary is six-dimensional.",
        color=MUTED,
        fontsize=10.8,
        ha="left",
    )
    fig.text(
        0.055,
        0.070,
        "Surface: typed generic implicit field    |    Lines: projected R^7 basis    |    Dashed: guard n_z=0",
        color=TEXT,
        fontsize=10.5,
        ha="left",
    )
    fig.text(
        0.055,
        0.038,
        f"White route: state_at path    |    Red points: verified crossings    |    ternary address: {address_text}",
        color=MUTED,
        fontsize=10.0,
        ha="left",
    )
    fig.text(
        0.955,
        0.040,
        f"(t, phase, lift, profile)=({hidden.time:.2f}, {hidden.phase:.2f}, {hidden.route_lift:.2f}, {hidden.profile:.2f})",
        color=MUTED,
        fontsize=9.5,
        ha="right",
    )
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.10, top=0.90)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)

    return {
        "vertices": int(len(vertices)),
        "triangles": int(len(faces)),
        "radius_min": float(radii.min()),
        "radius_max": float(radii.max()),
        "events": event_records,
    }


def render_animation(output: Path, address: np.ndarray, config: RenderConfig) -> dict:
    vertices, faces, radii, normals_param = uv_sphere_mesh(
        config.theta_samples_animation,
        config.phi_samples_animation,
        hidden_state_at(0.0),
        address,
        config,
    )
    elev0, azim0 = 20.0, 25.0
    colors = face_colors(vertices, faces, radii, elev0, azim0)

    fig = plt.figure(figsize=(7.2, 7.2), dpi=100)
    ax = setup_3d_axis(fig, elev0, azim0)
    poly = Poly3DCollection(vertices[faces], facecolors=colors, edgecolors="none", linewidths=0.0, antialiased=False, zorder=2)
    poly.set_zsort("average")
    ax.add_collection3d(poly)
    add_axis_guides(ax)

    hidden0 = hidden_state_at(0.0)
    route_line, guard_line, event_scatter, _ = add_context_artists(ax, hidden0, address, config)
    title = fig.text(
        0.05,
        0.95,
        "TKM 1.0 - bounded hidden-coordinate flow",
        color=TEXT,
        fontsize=14,
        fontweight="bold",
        ha="left",
        va="top",
    )
    status = fig.text(0.05, 0.05, "", color=MUTED, fontsize=9.5, ha="left", va="bottom")
    fig.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=1.0)

    metadata = {
        "title": "Tom Klootwijk Manifold numerical render",
        "artist": "Deterministic Python renderer",
        "comment": "3D position slices of the formal TKM 1.0 implicit boundary",
    }
    writer = FFMpegWriter(fps=config.animation_fps, metadata=metadata, bitrate=3200)
    output.parent.mkdir(parents=True, exist_ok=True)

    radius_min = math.inf
    radius_max = -math.inf
    with writer.saving(fig, str(output), dpi=100):
        for frame in range(config.animation_frames):
            tau = TAU * frame / config.animation_frames
            hidden = hidden_state_at(tau)
            radii = radius_on_sphere(normals_param, hidden, address, config)
            vertices = normals_param * radii[:, None]
            radius_min = min(radius_min, float(radii.min()))
            radius_max = max(radius_max, float(radii.max()))

            elev = 18.0 + 8.0 * math.sin(tau)
            azim = 25.0 + 360.0 * frame / config.animation_frames
            ax.view_init(elev=elev, azim=azim)
            poly.set_verts(vertices[faces])
            poly.set_facecolor(face_colors(vertices, faces, radii, elev, azim))

            _, route = surface_route(hidden, address, config, samples=241)
            ring = guard_ring(hidden, address, config, samples=181)
            events, _ = verified_event_points(hidden, address, config)
            route_draw = route * 1.018
            ring_draw = ring * 1.014
            events_draw = events * 1.024
            route_line.set_data_3d(route_draw[:, 0], route_draw[:, 1], route_draw[:, 2])
            guard_line.set_data_3d(ring_draw[:, 0], ring_draw[:, 1], ring_draw[:, 2])
            event_scatter._offsets3d = (events_draw[:, 0], events_draw[:, 1], events_draw[:, 2])  # Matplotlib 3D API

            status.set_text(
                f"t={hidden.time:5.2f}   phase={hidden.phase:5.2f}   route_lift={hidden.route_lift:5.2f}   "
                f"profile={hidden.profile:5.2f}\n"
                "surface=f^{-1}(0) slice   |   white=state_at route   |   red=verified guard crossings"
            )
            writer.grab_frame(facecolor=fig.get_facecolor())

    plt.close(fig)
    return {
        "frames": config.animation_frames,
        "fps": config.animation_fps,
        "vertices_per_frame": int(len(vertices)),
        "triangles_per_frame": int(len(faces)),
        "radius_min_over_frames": radius_min,
        "radius_max_over_frames": radius_max,
    }


def export_glb(
    output: Path,
    hidden: HiddenState,
    address: np.ndarray,
    config: RenderConfig,
) -> dict | None:
    if trimesh is None:
        return None
    vertices, faces, radii, _ = uv_sphere_mesh(
        config.theta_samples_still,
        config.phi_samples_still,
        hidden,
        address,
        config,
    )
    lo, hi = np.percentile(radii, [2.0, 98.0])
    x = np.clip((radii - lo) / max(hi - lo, 1.0e-12), 0.0, 1.0)
    rgba = (cm.viridis(x) * 255.0).astype(np.uint8)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, vertex_colors=rgba, process=False)
    output.write_bytes(mesh.export(file_type="glb"))
    return {
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "euler_number": int(mesh.euler_number),
        "components": int(len(mesh.split(only_watertight=False))),
        "volume": float(mesh.volume),
        "area": float(mesh.area),
    }


def export_interactive_html(
    output: Path,
    hidden: HiddenState,
    address: np.ndarray,
    config: RenderConfig,
) -> dict | None:
    if go is None or pio is None:
        return None
    # Moderate resolution keeps the standalone HTML responsive.
    vertices, faces, radii, _ = uv_sphere_mesh(101, 200, hidden, address, config)
    _, route = surface_route(hidden, address, config, samples=501)
    ring = guard_ring(hidden, address, config, samples=401)
    events, _ = verified_event_points(hidden, address, config)

    fig = go.Figure()
    fig.add_trace(
        go.Mesh3d(
            x=vertices[:, 0],
            y=vertices[:, 1],
            z=vertices[:, 2],
            i=faces[:, 0],
            j=faces[:, 1],
            k=faces[:, 2],
            intensity=radii,
            colorscale="Viridis",
            showscale=False,
            opacity=1.0,
            flatshading=False,
            lighting=dict(ambient=0.28, diffuse=0.75, specular=0.45, roughness=0.42, fresnel=0.15),
            lightposition=dict(x=-2.0, y=-1.0, z=3.0),
            name="f=0 slice",
            hovertemplate="x=%{x:.4f}<br>y=%{y:.4f}<br>z=%{z:.4f}<extra>TKM boundary slice</extra>",
        )
    )
    for k, direction in enumerate(AXES, start=1):
        t = np.array([-1.45, 1.45])
        fig.add_trace(
            go.Scatter3d(
                x=t * direction[0], y=t * direction[1], z=t * direction[2],
                mode="lines", line=dict(width=3), name=f"projected e{k}", showlegend=False,
                hoverinfo="skip",
            )
        )
    fig.add_trace(
        go.Scatter3d(
            x=route[:, 0], y=route[:, 1], z=route[:, 2],
            mode="lines", line=dict(width=5), name="state_at route",
        )
    )
    fig.add_trace(
        go.Scatter3d(
            x=ring[:, 0], y=ring[:, 1], z=ring[:, 2],
            mode="lines", line=dict(width=4, dash="dash"), name="guard n_z=0",
        )
    )
    fig.add_trace(
        go.Scatter3d(
            x=events[:, 0], y=events[:, 1], z=events[:, 2],
            mode="markers", marker=dict(size=6), name="verified crossings",
        )
    )
    fig.update_layout(
        title="Tom Klootwijk Manifold - interactive numerical slice",
        paper_bgcolor="rgb(5,8,14)",
        plot_bgcolor="rgb(5,8,14)",
        font=dict(color="rgb(235,241,247)"),
        scene=dict(
            aspectmode="cube",
            xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
            camera=dict(eye=dict(x=1.45, y=1.25, z=0.85)),
            bgcolor="rgb(5,8,14)",
        ),
        margin=dict(l=0, r=0, t=48, b=0),
        legend=dict(x=0.01, y=0.99),
        annotations=[
            dict(
                text="3D position slice of the regular 6D zero boundary; seven R^7 basis axes are shown after projection.",
                x=0.5, y=0.01, xref="paper", yref="paper", showarrow=False,
            )
        ],
    )
    pio.write_html(fig, file=str(output), include_plotlyjs=True, full_html=True, auto_open=False)
    return {"vertices": int(len(vertices)), "triangles": int(len(faces))}


def finite_difference_gradient_norms(
    points: np.ndarray,
    hidden: HiddenState,
    address: np.ndarray,
    config: RenderConfig,
    step: float = 1.0e-5,
) -> np.ndarray:
    grads = np.empty_like(points)
    for axis in range(3):
        delta = np.zeros(3)
        delta[axis] = step
        grads[:, axis] = (
            field_value(points + delta, hidden, address, config)
            - field_value(points - delta, hidden, address, config)
        ) / (2.0 * step)
    return np.linalg.norm(grads, axis=1)


def validate_instance(
    hidden: HiddenState,
    address: np.ndarray,
    config: RenderConfig,
) -> dict:
    vertices, faces, radii, _ = uv_sphere_mesh(121, 240, hidden, address, config)
    residual = np.abs(field_value(vertices, hidden, address, config))

    rng = np.random.default_rng(943937)
    take = rng.choice(len(vertices), size=min(2500, len(vertices)), replace=False)
    gradient_norms = finite_difference_gradient_norms(vertices[take], hidden, address, config)

    mesh_checks = None
    if trimesh is not None:
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        mesh_checks = {
            "watertight": bool(mesh.is_watertight),
            "winding_consistent": bool(mesh.is_winding_consistent),
            "euler_number": int(mesh.euler_number),
            "components": int(len(mesh.split(only_watertight=False))),
        }

    # Conservative analytic lower bound on R for address symbols in {0,1,2}, |profile|<=1:
    # g_j >= -1/12; w_j <= (0.48+0.34*2)*(1+0.15+0.06+0.03) = 1.4384.
    # L >= -1.4384/12. H,C >= -1.
    max_weight_bound = (0.48 + 0.34 * 2.0) * (1.0 + 0.15 + 0.06 + 0.03)
    radius_lower_bound = (
        1.0
        - config.amplitude_axes * max_weight_bound / 12.0
        - config.amplitude_ternary
        - config.amplitude_vertical
    )

    return {
        "field_kind": "generic implicit field (not asserted to be exact signed distance)",
        "ambient_dimension": 7,
        "regular_boundary_dimension": 6,
        "visible_slice_dimension": 2,
        "zero_set_residual_max": float(residual.max()),
        "zero_set_residual_rms": float(np.sqrt(np.mean(residual**2))),
        "finite_difference_gradient_norm_min": float(gradient_norms.min()),
        "finite_difference_gradient_norm_median": float(np.median(gradient_norms)),
        "finite_difference_gradient_norm_max": float(gradient_norms.max()),
        "analytic_regularity_argument": (
            "For f(p,h)=||p||-R(p/||p||,h), the radial derivative is exactly 1 on the zero set. "
            "Because the certified radius is positive, p is nonzero there; therefore df cannot vanish."
        ),
        "analytic_radius_lower_bound": float(radius_lower_bound),
        "sampled_radius_min": float(radii.min()),
        "sampled_radius_max": float(radii.max()),
        "mesh": mesh_checks,
    }


def write_spec(
    output: Path,
    hidden: HiddenState,
    address: np.ndarray,
    config: RenderConfig,
    validation: dict,
    still_stats: dict,
    animation_stats: dict,
    glb_stats: dict | None,
    html_stats: dict | None,
) -> None:
    spec = {
        "schema": "tkm-render-1.0",
        "title": "Tom Klootwijk Manifold numerical rendering instance",
        "attribution": {
            "name": "Tom Klootwijk",
            "requester_supplied_identifier": "NL200678942",
            "requester_supplied_date_of_birth": "1990-07-10",
            "verification_status": "requester-supplied-not-independently-verified",
        },
        "ambient": {
            "dimension": 7,
            "coordinates": ["x", "y", "z", "time", "phase", "route_lift", "profile"],
            "model": "R3_position x R_time x S1_phase x R_route_lift x R_profile",
            "metric": "Euclidean product metric for this rendering instance",
        },
        "field": {
            "kind": "generic implicit field",
            "domain": "p != 0 and |profile| <= 1",
            "formula": "f(p,h)=||p||-R(p/||p||,h)",
            "axis_basis": "g_j(n)=(13*(n dot d_j)^12-1)/12",
            "axis_term": "L(n,h)=(1/7)*sum_j w_j(h)*g_j(n)",
            "ternary_term": "H=0.72 Re((nx+i ny)^3 e^{i a}) + 0.20 Re((nx+i ny)^9 e^{i b}) + 0.08 Re((nx+i ny)^27 e^{i c})",
            "vertical_term": "C=(1-nz^2) sin(4 nz + route_lift + 0.25 time)",
            "radius": "R=1+1.50 L+0.18 H+0.07 C",
            "zero_level": 0.0,
            "exact_sdf_claim": False,
            "regularity_required": True,
        },
        "projection": {
            "description": "Fixed 3x7 Fourier projection of the seven orthogonal ambient basis axes",
            "matrix_rows_are_orthonormal": True,
            "matrix": P_MATRIX.tolist(),
            "normalized_axis_images": AXES.tolist(),
        },
        "address": {
            "decimal_label": config.address_decimal,
            "alphabet": [0, 1, 2],
            "ternary_symbols": [int(x) for x in address],
            "reserved_quaternary_code": 3,
            "semantic_role": "bounded parameter/address selector; not topology and not a one-bit mutation claim",
        },
        "visible_slice": asdict(hidden),
        "flow": {
            "family": "bounded deterministic closed expression",
            "time_parameter": "tau in [0,2pi)",
            "phase": "0.40+0.42 sin(tau)",
            "route_lift": "-0.60+0.28 cos(0.70 tau)",
            "profile": "0.55 sin(0.50 tau)",
        },
        "route_and_event": {
            "direction": "n(s)=(cos s, sin s cos 2s, sin s sin 2s)",
            "guard": "n_z=0",
            "verified_crossings": ["s=pi/2", "s=3pi/2"],
            "tangencies_not_committed_as_crossings": ["s=0", "s=pi", "s=2pi"],
        },
        "render_config": asdict(config),
        "validation": validation,
        "outputs": {
            "still": still_stats,
            "animation": animation_stats,
            "glb": glb_stats,
            "interactive_html": html_stats,
        },
    }
    output.write_text(json.dumps(spec, indent=2), encoding="utf-8")


def write_readme(output: Path, address: np.ndarray, validation: dict) -> None:
    address_text = "".join(str(int(x)) for x in address)
    text = f"""# Tom Klootwijk Manifold numerical render

This bundle contains a deterministic computational rendering of one **conforming instance** of the formal TKM 1.0 system. No image-generation model was used.

## What is rendered

The ambient coordinates are

`q = (x, y, z, time, phase, route_lift, profile)`

in a seven-dimensional product space. The typed field is a **generic implicit field**

`f(p,h) = ||p|| - R(p/||p||,h)`

and the Tom Klootwijk boundary is `B_TK = f^(-1)(0)`. The full regular boundary has dimension six. A monitor cannot directly display a six-dimensional set, so the PNG, MP4, GLB and HTML show the three-dimensional **position slice** obtained by fixing the four hidden coordinates. Its visible zero set is a smooth two-dimensional surface.

Seven mutually orthogonal coordinate axes in `R^7` are projected into `R^3` using the fixed matrix recorded in `Tom_Klootwijk_Manifold_Render_Spec.json`. They are guides, not claims that seven projected lines remain mutually orthogonal in three dimensions.

The bounded ternary address is `{address_text}` (decimal label 943). It modulates seven smooth axis terms. Frequencies 3, 9 and 27 form a finite depth-3 ternary harmonic grammar; this render does not claim an infinite Sierpinski boundary.

## Validation result

- Field kind: {validation['field_kind']}
- Maximum sampled zero residual: {validation['zero_set_residual_max']:.3e}
- Minimum finite-difference gradient norm: {validation['finite_difference_gradient_norm_min']:.6f}
- Conservative analytic radius lower bound: {validation['analytic_radius_lower_bound']:.6f}
- Sampled radius range: {validation['sampled_radius_min']:.6f} to {validation['sampled_radius_max']:.6f}
- Mesh check: {json.dumps(validation.get('mesh'), sort_keys=True)}

The regularity proof is structural: the radial derivative of `f` is exactly 1 on the zero set, so `df` cannot vanish there. This certifies the chosen field instance as a regular zero-level boundary on its declared domain; it does not certify unrelated physical, performance or authorship claims.

## Files

- `Tom_Klootwijk_Manifold_Render.png` - annotated high-resolution still.
- `Tom_Klootwijk_Manifold_Render.mp4` - bounded hidden-coordinate flow and turntable.
- `Tom_Klootwijk_Manifold_Render.glb` - canonical-slice 3D mesh.
- `Tom_Klootwijk_Manifold_Render.html` - interactive browser view.
- `Tom_Klootwijk_Manifold_Render_Spec.json` - exact formulas, parameters and validation.
- `Tom_Klootwijk_Manifold_Render_Events.json` - verified guard events for the displayed route.
- `render_tkm_manifold.py` - reproducible renderer.
- `SHA256SUMS.txt` - checksums.
"""
    output.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=Path("/mnt/data/tkm_render_output"))
    parser.add_argument("--skip-animation", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    config = RenderConfig()
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)

    hidden = canonical_hidden_state()
    address = base_digits(config.address_decimal, 3, config.address_width)

    validation = validate_instance(hidden, address, config)
    still_stats = render_still(out / "Tom_Klootwijk_Manifold_Render.png", hidden, address, config)

    if args.skip_animation:
        animation_stats = {"skipped": True}
    else:
        animation_stats = render_animation(out / "Tom_Klootwijk_Manifold_Render.mp4", address, config)

    glb_stats = export_glb(out / "Tom_Klootwijk_Manifold_Render.glb", hidden, address, config)
    html_stats = export_interactive_html(out / "Tom_Klootwijk_Manifold_Render.html", hidden, address, config)

    event_points, event_records = verified_event_points(hidden, address, config)
    (out / "Tom_Klootwijk_Manifold_Render_Events.json").write_text(
        json.dumps({"events": event_records, "points": event_points.tolist()}, indent=2), encoding="utf-8"
    )

    write_spec(
        out / "Tom_Klootwijk_Manifold_Render_Spec.json",
        hidden,
        address,
        config,
        validation,
        still_stats,
        animation_stats,
        glb_stats,
        html_stats,
    )
    write_readme(out / "README.md", address, validation)

    # Copy this exact script into the bundle if it was invoked from elsewhere.
    script_src = Path(__file__).resolve()
    script_dst = out / "render_tkm_manifold.py"
    if script_src != script_dst.resolve():
        shutil.copy2(script_src, script_dst)

    deliverables = sorted(p for p in out.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt")
    sums = "\n".join(f"{sha256_file(p)}  {p.name}" for p in deliverables) + "\n"
    (out / "SHA256SUMS.txt").write_text(sums, encoding="utf-8")

    bundle = out.parent / "Tom_Klootwijk_Manifold_Render_Bundle.zip"
    if bundle.exists():
        bundle.unlink()
    shutil.make_archive(str(bundle.with_suffix("")), "zip", root_dir=out)

    result = {
        "output_directory": str(out),
        "bundle": str(bundle),
        "validation": validation,
        "still": still_stats,
        "animation": animation_stats,
        "glb": glb_stats,
        "interactive_html": html_stats,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

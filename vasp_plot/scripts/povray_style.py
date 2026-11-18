"""POV-Ray look shared by ALL structure figures (user, 2026-11-17/18): atoms = polished billiard balls.

Import instead of re-typing the numbers:
    from povray_style import FIN, LIGHTS, atom_texture
Rules (why, see references/crystal-defect-renders.md):
  * FIN needs NON-shadowless lights (shadowless lights give no specular/phong); remove shadows per object
    with `no_shadow`, never with `shadowless`.
  * lights in FRONT of every object (z <= -500 for a camera at z = -1000).
  * do NOT add `reflection` (grainy surface).
  * sRGB colours go in as-is (no linearisation).
  * legend keys must be rendered spheres with this same FIN and LIGHTS (`key_sphere_pov`), not matplotlib circles.
"""
import math

# sharp white highlight + halo; 2nd faint highlight comes from the fill light
FIN = "finish { ambient 0.16 diffuse 0.72 specular 1.0 roughness 0.0015 phong 1.0 phong_size 70 }"
LIGHTS = ["light_source { <-250,250,-500> color rgb <1,1,1> }",            # key, upper-left-front
          "light_source { <300,-150,-400> color rgb <0.25,0.25,0.25> }"]   # fill, lower-right-front


def atom_texture(rgb):
    """POV-Ray texture of an atom; rgb = '<r,g,b>' in 0-1 sRGB."""
    return f"texture {{ pigment {{ rgb {rgb} }} {FIN} }}"


def key_sphere_pov(rgb, half=1.08):
    """Scene of ONE unit sphere (legend key), same finish/lights as the panels. Render square (e.g. 240x240 px)."""
    return "\n".join([
        "background { color rgb <1,1,1> }", "camera {", "  location <0,0,-1000>", "  look_at <0,0,0>",
        f"  angle {math.degrees(2 * math.atan(half / 1000)):.6f}", f"  right <{2 * half:.2f},0,0>",
        f"  up <0,{2 * half:.2f},0>", "}", *LIGHTS,
        f"sphere {{ <0,0,0>, 1 {atom_texture(rgb)} no_shadow }}"])

# ==============================================================================
# S.P.A.R.K. - Holographic Core Visualizer
# Version: 1.0 (Compatible with Python 3.12+ and Pyglet 2.x)
# ==============================================================================

import pyglet
import pyglet.text

## Removed import of main from spark.main (file does not exist)
pyglet.options['gl_error_check'] = True  # Helps debug OpenGL issues
pyglet.options['vsync'] = True  # Smooths animations
import numpy as np
import random
import time
import ctypes

# --- Compatibility Fix for Pyglet 2.x (The "Secret Map") ---
# This block loads the necessary OpenGL functions that were changed in new Pyglet versions.
import sys
if sys.platform == "win32":
    gl_lib = ctypes.windll.opengl32
    glu_lib = ctypes.windll.glu32
else:
    gl_lib = ctypes.cdll.LoadLibrary("libGL.so")
    glu_lib = ctypes.cdll.LoadLibrary("libGLU.so")

gl = pyglet.gl
glPointSize = ctypes.CFUNCTYPE(None, ctypes.c_float)(("glPointSize", gl_lib))
glColor4f = ctypes.CFUNCTYPE(None, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float)(("glColor4f", gl_lib))
glVertex3f = ctypes.CFUNCTYPE(None, ctypes.c_float, ctypes.c_float, ctypes.c_float)(("glVertex3f", gl_lib))
glClear = ctypes.CFUNCTYPE(None, ctypes.c_uint)(("glClear", gl_lib))
glEnable = ctypes.CFUNCTYPE(None, ctypes.c_uint)(("glEnable", gl_lib))
glBlendFunc = ctypes.CFUNCTYPE(None, ctypes.c_uint, ctypes.c_uint)(("glBlendFunc", gl_lib))
glMatrixMode = ctypes.CFUNCTYPE(None, ctypes.c_uint)(("glMatrixMode", gl_lib))
glLoadIdentity = ctypes.CFUNCTYPE(None)(("glLoadIdentity", gl_lib))
glRotatef = ctypes.CFUNCTYPE(None, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float)(("glRotatef", gl_lib))
glClearColor = ctypes.CFUNCTYPE(None, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float)(("glClearColor", gl_lib))
glBegin = ctypes.CFUNCTYPE(None, ctypes.c_uint)(("glBegin", gl_lib))
glEnd = ctypes.CFUNCTYPE(None)(("glEnd", gl_lib))
GL_COLOR_BUFFER_BIT = gl.GL_COLOR_BUFFER_BIT
GL_DEPTH_BUFFER_BIT = gl.GL_DEPTH_BUFFER_BIT
GL_POINTS = gl.GL_POINTS
GL_DEPTH_TEST = gl.GL_DEPTH_TEST
GL_BLEND = gl.GL_BLEND
GL_SRC_ALPHA = gl.GL_SRC_ALPHA
GL_ONE = gl.GL_ONE  # Use GL_ONE for a nice additive glow effect
# Add missing matrix mode constants
GL_PROJECTION = 0x1701
GL_MODELVIEW = 0x1700
def load_gl_func(lib, name, restype, argtypes):
    func = getattr(lib, name)
    func.restype = restype
    func.argtypes = argtypes
    return func

# Load required GLU functions
gluPerspective = load_gl_func(glu_lib, "gluPerspective", None, [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double])
gluLookAt = load_gl_func(glu_lib, "gluLookAt", None, [ctypes.c_double, ctypes.c_double, ctypes.c_double,
                                                     ctypes.c_double, ctypes.c_double, ctypes.c_double,
                                                     ctypes.c_double, ctypes.c_double, ctypes.c_double])
# Add glOrtho definition for OpenGL compatibility
if sys.platform == "win32":
    glOrtho = ctypes.CFUNCTYPE(None, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double)(('glOrtho', gl_lib))
else:
    glOrtho = ctypes.CFUNCTYPE(None, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double)(('glOrtho', gl_lib))
# --- Configuration ---
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800
NUM_PARTICLES = 5000  # More particles for a denser look
PARTICLE_SIZE = 2.5
BASE_RADIUS = 1.5

# S.P.A.R.K. States
IDLE = "idle"
LISTENING = "listening"
THINKING = "thinking"
SPEAKING = "speaking"


# --- Global State Management (The "Mood Ring") ---
# This variable will be controlled by other parts of S.P.A.R.K. later
current_spark_visual_state = IDLE

def set_spark_visual_state(state):
    """Call this function from other files to change the visual state."""
    global current_spark_visual_state
    current_spark_visual_state = state
    print(f"[SPARK VISUAL] State changed to: {state}")


# --- Particle & Core Classes ---
class Particle:
    def __init__(self, position, velocity, color, lifespan):
        self.position = np.array(position, dtype=np.float32)
        self.velocity = np.array(velocity, dtype=np.float32)
        self.color = np.array(color, dtype=np.float32)
        self.lifespan = lifespan
        self.age = 0.0

    def update(self, dt):
        self.position += self.velocity * dt
        self.age += dt
        # Fade out effect
        self.color[3] = max(0.0, 1.0 - (self.age / self.lifespan))

    def is_alive(self):
        return self.age < self.lifespan

class HolographicCore:
    def __init__(self, num_particles):
        self.particles = []
        self.num_particles = num_particles
        self.rotation_angle = 0.0
        for _ in range(self.num_particles):
            self.spawn_particle()

    def spawn_particle(self):
        # Spawn particles in a sphere for a 3D look
        phi = random.uniform(0, 2 * np.pi)
        costheta = random.uniform(-1, 1)
        theta = np.arccos(costheta)
        r = BASE_RADIUS * (random.uniform(0.9, 1.1)) # Give it some depth

        x = r * np.sin(theta) * np.cos(phi)
        y = r * np.sin(theta) * np.sin(phi)
        z = r * np.cos(theta)
        
        position = [x, y, z]
        velocity = np.array(position) * random.uniform(-0.1, 0.1) # Random initial drift
        color = [1.0, 0.6, 0.1, 1.0] # Glowing orange
        lifespan = random.uniform(1.0, 2.5)
        
        self.particles.append(Particle(position, velocity, color, lifespan))

    def update(self, dt):
        self.rotation_angle += 10 * dt # Gentle constant rotation
        
        new_particles = []
        for p in self.particles:
            if p.is_alive():
                # Apply effects based on S.P.A.R.K.'s current state
                if current_spark_visual_state == LISTENING:
                    # Pull particles towards the center
                    p.velocity -= p.position * 0.5 * dt
                elif current_spark_visual_state == THINKING:
                    # Agitated, faster movement
                    random_push = np.random.randn(3) * 0.5
                    p.velocity += random_push * dt
                    p.color[:3] = [1.0, 1.0, 0.5] # Brighter, yellow-white sparks
                elif current_spark_visual_state == SPEAKING:
                    # Push particles gently outwards
                    p.velocity += p.position * 0.3 * dt
                
                p.update(dt)
                new_particles.append(p)
            else:
                self.spawn_particle() # Replace dead particles with new ones

        self.particles = new_particles

    def draw(self):
        glPointSize(PARTICLE_SIZE)
        glBegin(GL_POINTS)
        for p in self.particles:
            glColor4f(*p.color)
            glVertex3f(*p.position)
        glEnd()

# --- Pyglet Window and Event Setup ---
config = pyglet.gl.Config(
    buffer_size=24,           # Depth buffer bits
    double_buffer=True,       # Use double buffering for smooth animation
    alpha_size=8,             # For transparency
    sample_buffers=1,         # For anti-aliasing (smooth edges)
    samples=4,                # Number of samples for anti-aliasing
    depth_size=24             # Ensure good depth precision
)
window = pyglet.window.Window(WINDOW_WIDTH, WINDOW_HEIGHT, caption='S.P.A.R.K. Core', config=config, resizable=True)
core = HolographicCore(NUM_PARTICLES)

live_transcription = ""

@window.event
def on_draw():
    # Clear both color and depth buffers
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    # Set projection matrix
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    aspect = window.width / float(window.height)
    gluPerspective(60.0, aspect, 0.1, 100.0)

    # Set modelview matrix
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    gluLookAt(0, 0, 5,  # Camera is 5 units back
              0, 0, 0,  # Look at the center of the world
              0, 1, 0)  # Up is the positive Y axis

    # Rotate the entire core
    glRotatef(core.rotation_angle, 0.2, 1, 0)

    # Set color and size based on state
    state = current_spark_visual_state
    if state == "idle":
        color = [1.0, 0.6, 0.1, 1.0]  # Orange
        size = 2.5
    elif state == "listening":
        color = [0.2, 0.8, 1.0, 1.0]  # Blue
        size = 3.5
    elif state == "thinking":
        color = [1.0, 1.0, 0.5, 1.0]  # Yellow-white
        size = 4.0
    elif state == "speaking":
        color = [0.8, 1.0, 0.2, 1.0]  # Greenish
        size = 3.0
    else:
        color = [1.0, 0.6, 0.1, 1.0]
        size = 2.5

    # Draw the actual core with state color/size
    glPointSize(size)
    glBegin(GL_POINTS)
    for p in core.particles:
        glColor4f(*color)
        glVertex3f(*p.position)
    glEnd()

    # Draw the current state as text overlay
    label = pyglet.text.Label(
        f"State: {state.upper()}",
        font_name='Consolas',
        font_size=18,
        x=20, y=window.height - 40,
        anchor_x='left', anchor_y='top',
        color=(255, 255, 255, 200)
    )
    # Switch to 2D rendering for text
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0, window.width, 0, window.height, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    label.draw()

    # Draw the live transcription as overlay
    if live_transcription:
        transcript_label = pyglet.text.Label(
            f"You: {live_transcription}",
            font_name='Consolas',
            font_size=16,
            x=20, y=window.height - 70,
            anchor_x='left', anchor_y='top',
            color=(0, 255, 180, 220)
        )
        transcript_label.draw()


# Handle window resize to update viewport and projection
@window.event
def on_resize(width, height):
    gl.glViewport(0, 0, width, height)
    return pyglet.event.EVENT_HANDLED

def update(dt):
    core.update(dt)

def setup_gl():
    # Request a core OpenGL profile if available, for modern rendering
    try:
        pyglet.gl.current_context.set_current()
        pyglet.gl.current_context.set_info(pyglet.gl.ContextInfo(major_version=3, minor_version=3, forward_compatible=True, profile='core'))
    except Exception as e:
        print(f"Warning: Could not get a modern OpenGL context. Falling back to default. {e}")
        # If modern context fails, proceed with default.
    glClearColor(0.0, 0.05, 0.1, 1.0) # Dark blue space background
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    # Standard blending for transparency
    glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

# --- Main Application Logic ---
def run_visual():
    setup_gl()
    pyglet.clock.schedule_interval(update, 1/60.0) # Update 60 times a second

    pyglet.app.run()

if __name__ == '__main__':
    run_visual()
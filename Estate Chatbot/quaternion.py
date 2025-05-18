import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import random
import time

class CelestialBody:
    def __init__(self, mass, position, velocity, radius):
        self.mass = mass
        self.position = np.array(position)
        self.velocity = np.array(velocity)
        self.radius = radius

class NBodySimulation:
        
    def __init__(self, bodies, collision_handling="elastic"):
        self.bodies = bodies
        self.collision_events = []
        self.collision_handling = collision_handling

    def gravitational_force(self, body1, body2):
        G = 6.67430e-11
        r_vector = body2.position - body1.position
        distance = np.linalg.norm(r_vector)
        force_magnitude = G * body1.mass * body2.mass / (distance**2)
        force_direction = r_vector / distance
        return force_direction * force_magnitude

    def step(self, dt):
        num_bodies = len(self.bodies)
        
        # Calculate accelerations
        accelerations = [np.zeros(3) for _ in self.bodies]
        for i in range(num_bodies):
            for j in range(i + 1, num_bodies):
                force_vector = self.gravitational_force(self.bodies[i], self.bodies[j])
                accelerations[i] += force_vector / self.bodies[i].mass
                accelerations[j] -= force_vector / self.bodies[j].mass
        
        # Update positions and velocities
        for i in range(num_bodies):
            self.bodies[i].velocity += accelerations[i] * dt
            self.bodies[i].position += self.bodies[i].velocity * dt
        
        # Check for collisions (basic bounding sphere collision detection)
        self.collision_events = []
        for i in range(num_bodies):
            for j in range(i + 1, num_bodies):
                r_vector = self.bodies[j].position - self.bodies[i].position
                distance = np.linalg.norm(r_vector)
                if distance < (self.bodies[i].radius + self.bodies[j].radius):
                    self.collision_events.append((i, j))
                    
                    # Handle collision based on type
                    if self.collision_handling == "elastic":
                        self.handle_elastic_collision(i, j)

    def handle_elastic_collision(self, i, j):
        body1 = self.bodies[i]
        body2 = self.bodies[j]
        
        r_vector = body2.position - body1.position
        distance = np.linalg.norm(r_vector)
        normal_unit_vector = r_vector / distance
        
        # Relative velocity along the normal
        v_relative = (body2.velocity - body1.velocity) @ normal_unit_vector
        
        if v_relative < 0:
            return
        
        restitution_coefficient = 0.8
        
        impulse_magnitude = -(1 + restitution_coefficient) * v_relative / (
            1 / body1.mass + 1 / body2.mass
        )
        
        impulse_vector = impulse_magnitude * normal_unit_vector
        
        # Update velocities
        body1.velocity += impulse_vector / body1.mass
        body2.velocity -= impulse_vector / body2.mass

    def run_simulation(self, total_time, dt):
        steps = int(total_time // dt)
        for _ in range(steps):
            self.step(dt)

    def total_energy(self):
        G = 6.67430e-11
        kinetic_energy = 0.5 * sum(body.mass * np.linalg.norm(body.velocity)**2 for body in self.bodies)
        potential_energy = 0
        num_bodies = len(self.bodies)
        
        for i in range(num_bodies):
            for j in range(i + 1, num_bodies):
                r_vector = self.bodies[j].position - self.bodies[i].position
                distance = np.linalg.norm(r_vector)
                potential_energy -= G * self.bodies[i].mass * self.bodies[j].mass / distance
        
        return kinetic_energy, potential_energy

class PhysicsSimulationVisualizer:
    def __init__(self, simulation):
        self.simulation = simulation

    def interactive_simulation(self, total_time, dt, fps):
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        bodies = self.simulation.bodies

        # Initial positions
        positions = np.array([body.position for body in bodies])
        scatter = ax.scatter(positions[:, 0], positions[:, 1], positions[:, 2], s=[body.radius / 1e6 for body in bodies])

        def update(frame):
            for _ in range(fps):
                self.simulation.step(dt / fps)

            pos = np.array([body.position for body in bodies])
            
            ax.clear()
            ax.set_xlim3d(pos[:, 0].min() - 1e11, pos[:, 0].max() + 1e11)
            ax.set_ylim3d(pos[:, 1].min() - 1e11, pos[:, 1].max() + 1e11)
            ax.set_zlim3d(pos[:, 2].min() - 1e11, pos[:, 2].max() + 1e11)
            ax.set_title("N-Body Simulation")

            scatter = ax.scatter(pos[:, 0], pos[:, 1], pos[:, 2],
                                 s=[body.radius / 1e6 for body in bodies],
                                 c=['blue', 'orange', 'green', 'red', 'purple'])

            return scatter,

        # ✅ Save reference to animation object
        ani = animation.FuncAnimation(fig, update, frames=int(total_time / dt), interval=1000 / fps)
        plt.show()

    def animate_simulation(self, total_time, dt, fps):
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        
        bodies = self.simulation.bodies
        scatter = ax.scatter([], [], [])
        
        positions = []
        radii = [body.radius for body in bodies]
        colors = ['blue' if i == 0 else 'orange' for i in range(len(bodies))]
        
        def update(frame):
            for _ in range(fps):
                self.simulation.step(dt / fps)
            
            pos = np.array([body.position for body in bodies])
            positions.append(pos.copy())
        
        ani = animation.FuncAnimation(fig, update, frames=int(total_time / dt), interval=dt, blit=False)
        
        # Save the animation as a video file
        ani.save('n_body_simulation.mp4', fps=fps)
        return ani

# Helper functions to create different simulations
def create_solar_system_simulation():
    sun = CelestialBody(1.989e30, [0, 0, 0], [0, 0, 0], 695700)
    earth = CelestialBody(5.972e24, [149.6e9, 0, 0], [0, 29783, 0], 6371e3)
    return NBodySimulation([sun, earth])

def create_binary_star_system():
    star1 = CelestialBody(1.0e30, [-1e11, 0, 0], [0, 50, 0], 7e8)
    star2 = CelestialBody(1.0e30, [1e11, 0, 0], [0, -50, 0], 7e8)
    return NBodySimulation([star1, star2])

def create_three_body_problem():
    body1 = CelestialBody(1.0e30, [-1e11, 0, 0], [0, 50, 0], 7e8)
    body2 = CelestialBody(1.0e30, [1e11, 0, 0], [0, -50, 0], 7e8)
    body3 = CelestialBody(1.0e24, [0, 0, 0], [0, 0, 0], 7e6)
    return NBodySimulation([body1, body2, body3])

def create_chaotic_multi_body_system(num_bodies):
    bodies = []
    for _ in range(num_bodies):
        mass = random.uniform(1.0e24, 1.0e30)
        position = np.array([random.uniform(-1e12, 1e12) for _ in range(3)])
        velocity = np.array([random.uniform(-100, 100) for _ in range(3)])
        radius = random.uniform(1e7, 1e8)
        bodies.append(CelestialBody(mass, position, velocity, radius))
    return NBodySimulation(bodies)

def test_simulation(simulation):
    kinetic_energy, potential_energy = simulation.learn_data_from_web()
    print(f"Kinetic Energy: {kinetic_energy}, Potential Energy: {potential_energy}")
    print("Running simulation...")
    for i in range(10):
        print(f"Frame {i}:")
        for body in simulation.bodies:
            print(f"  Position: {body.position}, Velocity: {body.velocity}")
        simulation.step(1.0e7)

# Example usage
if __name__ == "__main__":
    from matplotlib import animation


    
    # Create a chaotic multi-body system with 5 bodies
    simulation = create_chaotic_multi_body_system(5)
    
    # Visualize the simulation interactively
    visualizer = PhysicsSimulationVisualizer(simulation)
    visualizer.interactive_simulation(total_time=1e8, dt=1.0e7, fps=30)

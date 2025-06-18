import math
from random import Random
import numpy as np

_PI = math.pi
class SpinSystem:
    def __init__(self, random_generator, num_groups, num_spins_per_group, T, J, nu, p_spin_up=0.5, time_delay=0, dynamics='metropolis'):
        self.random_generator = random_generator
        self.num_groups = num_groups
        self.num_spins_per_group = num_spins_per_group
        self.T = T
        self.J = J
        self.nu = nu
        self.p_spin_up = p_spin_up
        self.spins = np.array([[1 if Random.uniform(self.random_generator, 0, 1) < self.p_spin_up else 0
                                for _ in range(self.num_spins_per_group)] for _ in range(self.num_groups)], dtype=np.uint8)
        self.spins_history = [self.spins.copy()]
        self.time_delay = time_delay
        self.dynamics = dynamics
        group_angles = np.linspace(0, 2 * _PI, num_groups, endpoint=False)
        self.angles = np.repeat(group_angles, self.num_spins_per_group)
        self.external_field = np.zeros(self.num_groups * self.num_spins_per_group)
        self.avg_direction = None
        # Precalcola la matrice J
        self.J_matrix = self._precompute_j_matrix()

    def _precompute_j_matrix(self):
        angle_diff_matrix = np.abs(np.subtract.outer(self.angles, self.angles))
        angle_diff_matrix = np.minimum(angle_diff_matrix, 2 * _PI - angle_diff_matrix)
        return np.cos(_PI * ((angle_diff_matrix / _PI) ** self.nu))

    def set_p_spin_up(self, p_spin_up):
        self.p_spin_up = p_spin_up

    def calculate_hamiltonian(self, state):
        state_flat = state.ravel()
        spin_interaction_matrix = np.outer(state_flat, state_flat)
        H_spin_interactions = -(self.J / (self.num_spins_per_group * self.num_groups)) * (self.J_matrix * spin_interaction_matrix)
        H_spin_interactions = np.sum(np.triu(H_spin_interactions, 1))
        external_field_contribution = -np.dot(self.external_field, state_flat)
        return H_spin_interactions + external_field_contribution

    def step(self, timedelay=True, dt=0.1, tau=33):
        i = Random.randint(self.random_generator, 0, self.num_groups - 1)
        j = Random.randint(self.random_generator, 0, self.num_spins_per_group - 1)
        # Usa direttamente la vista 1D se serve
        if timedelay and self.spins_history:
            hybrid_state = self.spins_history[-1].copy()
            hybrid_state[i, j] = self.spins[i, j]
            state_to_use = hybrid_state
        else:
            state_to_use = self.spins
        current_hamiltonian = self.calculate_hamiltonian(state_to_use)
        state_to_use[i, j] ^= 1
        new_hamiltonian = self.calculate_hamiltonian(state_to_use)
        delta_h = new_hamiltonian - current_hamiltonian
        if self.dynamics == 'metropolis':
            self._metropolis_acceptance(i, j, delta_h)
        elif self.dynamics == 'glauber':
            self._glauber_acceptance(i, j, delta_h, dt, tau)
        else:
            raise ValueError(f"Unknown dynamics type: {self.dynamics}")
        self.spins_history.append(self.spins.copy())

    def _metropolis_acceptance(self, i, j, delta_h):
        if delta_h <= 0 or Random.uniform(self.random_generator, 0, 1) < math.exp(-delta_h / self.T):
            self.spins[i, j] ^= 1

    def _glauber_acceptance(self, i, j, delta_h, dt, tau):
        G = self.num_groups
        N = self.num_spins_per_group
        acceptance_prob = (G * N * dt) / tau * (1 / (1 + math.exp(delta_h / self.T)))
        acceptance_prob = min(acceptance_prob, 1.0)
        if Random.uniform(self.random_generator, 0, 1) < acceptance_prob:
            self.spins[i, j] ^= 1

    def run_spins(self, steps=1, dt=0.1, tau=33):
        for _ in range(steps):
            self.step(dt=dt, tau=tau)
        return self.spins

    def average_direction_of_activity(self):
        flattened_spins = self.spins.ravel()
        if np.all(flattened_spins == 1):
            self.avg_direction = None
            return None
        unit_vectors = np.exp(1j * self.angles)
        active_mask = flattened_spins == 1
        sum_vector = np.sum(unit_vectors[active_mask])
        if sum_vector != 0:
            self.avg_direction = math.atan2(sum_vector.imag, sum_vector.real)
        else:
            self.avg_direction = None
        return self.avg_direction

    def get_avg_direction_of_activity(self):
        return self.avg_direction

    def get_inverse_magnitude_of_activity(self):
        flattened_spins = self.spins.ravel()
        unit_vectors = np.exp(1j * self.angles)
        active_mask = flattened_spins == 1
        sum_vector = np.sum(unit_vectors[active_mask])
        magnitude = abs(sum_vector)
        return 1 / magnitude if magnitude != 0 else float('inf')

    def get_width_of_activity(self):
        flattened_spins = self.spins.ravel()
        active_mask = flattened_spins == 1
        active_angles = self.angles[active_mask]
        if len(active_angles) > 1:
            unit_vectors = np.exp(1j * active_angles)
            R = abs(np.mean(unit_vectors))
            if R > 0:
                circ_std = math.sqrt(-2 * math.log(R))
                return circ_std
        return None

    def reset_spins(self):
        self.spins = np.array([[1 if Random.uniform(self.random_generator, 0, 1) < self.p_spin_up else 0
                                for _ in range(self.num_spins_per_group)] for _ in range(self.num_groups)], dtype=np.uint8)
        self.spins_history = [self.spins.copy()]

    def update_external_field(self, perceptual_outputs):
        self.external_field = perceptual_outputs

    def get_states(self):
        return self.spins

    def get_external_field(self):
        return self.external_field

    def get_angles(self):
        return (self.angles, self.num_groups, self.num_spins_per_group)

    def set_states(self, states):
        if states.shape != self.spins.shape:
            raise ValueError(f"Invalid shape for spin states. Expected {self.spins.shape}, but got {states.shape}.")
        self.spins = states.copy()
        self.spins_history.append(self.spins.copy())

    def sense_other_ring(self, other_ring_states, gain=1.0):
        self.external_field = gain * other_ring_states.ravel()
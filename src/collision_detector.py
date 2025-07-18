import multiprocessing as mp
from geometry_utils.vector3D import Vector3D

class CollisionDetector:
    def __init__(self, arena_shape, collisions):
        self.arena_shape = arena_shape
        self.collisions = collisions

    def run(self, dec_agents_in: mp.Queue, dec_agents_out: mp.Queue, dec_arena_in: mp.Queue):
        self.agents, self.objects = {}, {}
        while True:
            out = {}
            if dec_arena_in.qsize() > 0:
                self.objects = dec_arena_in.get()["objects"]
            if dec_agents_in.qsize() > 0:
                self.agents = dec_agents_in.get()["agents"]
                for k, (shapes, velocities, vectors, positions, names) in self.agents.items():
                    n_shapes = len(shapes)
                    out_tmp = [None] * n_shapes
                    for n in range(n_shapes):
                        shape = shapes[n]
                        max_velocity = velocities[n]
                        forward_vector = vectors[n]
                        position = positions[n]
                        name = names[n]
                        correction = None
                        contra_move_sum = Vector3D()
                        contra_norm_sum = Vector3D()
                        separations = []
                        if self.collisions:
                            # Collisions with other agents
                            for dshapes, dvelocities, dvectors, dpositions, dnames in self.agents.values():
                                for m, dshape in enumerate(dshapes):
                                    dforward_vector = dvectors[m]
                                    dposition = dpositions[m]
                                    dname = dnames[m]
                                    if name == dname:
                                        continue
                                    delta = Vector3D(position.x - dposition.x, position.y - dposition.y, 0)
                                    sum_radius = shape.get_radius() + dshape.get_radius()
                                    actual_distance = delta.magnitude()
                                    if actual_distance > sum_radius:
                                        continue
                                    overlap = shape.check_overlap(dshape)
                                    if overlap[0]:
                                        if correction is None:
                                            correction = position
                                        collision_normal = get_collision_normal(overlap[1], dshape, max_velocity)
                                        velocity_projection = collision_normal - forward_vector + dforward_vector
                                        contra_norm_sum += collision_normal
                                        contra_move_sum += dforward_vector
                                        penetration_depth = sum_radius - actual_distance
                                        norm_delta = delta.normalize()
                                        separations.append((norm_delta, penetration_depth * 0.1))
                                        correction = correction + velocity_projection
                            # Collisions with objects
                            for dshapes, dpositions in self.objects.values():
                                for m, dshape in enumerate(dshapes):
                                    dposition = dpositions[m]
                                    delta = Vector3D(position.x - dposition.x, position.y - dposition.y, 0)
                                    sum_radius = shape.get_radius() + dshape.get_radius()
                                    actual_distance = delta.magnitude()
                                    if actual_distance > sum_radius:
                                        continue
                                    overlap = shape.check_overlap(dshape)
                                    if overlap[0]:
                                        if correction is None:
                                            correction = position
                                        collision_normal = get_collision_normal(overlap[1], dshape, max_velocity)
                                        velocity_projection = collision_normal - forward_vector
                                        contra_norm_sum += collision_normal
                                        penetration_depth = sum_radius - actual_distance
                                        norm_delta = delta.normalize()
                                        separations.append((norm_delta, penetration_depth * 0.1))
                                        correction = correction + velocity_projection
                            if correction is not None:
                                shape.translate(correction)
                        # Collisions with arena borders
                        overlap = shape.check_overlap(self.arena_shape)
                        if overlap[0]:
                            if correction is None:
                                correction = position
                            collision_normal = get_collision_normal(overlap[1], self.arena_shape, max_velocity)
                            velocity_projection = collision_normal - forward_vector + contra_norm_sum - contra_move_sum
                            delta_arena = Vector3D(overlap[1].x, overlap[1].y, 0)
                            separations.append((delta_arena.normalize() * -0.001, 1))
                            correction = correction + velocity_projection
                        # Apply corrections
                        if correction is not None and separations:
                            total_separation = Vector3D()
                            for delta, penetration_depth in separations:
                                mag = delta.magnitude()
                                if mag > 0:
                                    sep = delta * penetration_depth
                                    total_separation += sep
                            correction = correction + total_separation
                        out_tmp[n] = correction
                    out[k] = out_tmp
                dec_agents_out.put(out)
    
def get_collision_normal(collision_point: Vector3D, shape, max_absolute_velocity: float) -> Vector3D:
    if shape._id == "circle":
        normal_vector = collision_point * -1
        return normal_vector.normalize() * max_absolute_velocity
    else:
        min_v = shape.min_vert()
        max_v = shape.max_vert()
        tmp_x, tmp_y = 0, 0
        if collision_point.x <= min_v.x:
            tmp_x = max_absolute_velocity
        elif collision_point.x >= max_v.x:
            tmp_x = -max_absolute_velocity
        if collision_point.y <= min_v.y:
            tmp_y = max_absolute_velocity
        elif collision_point.y >= max_v.y:
            tmp_y = -max_absolute_velocity
        return Vector3D(tmp_x, tmp_y, 0)
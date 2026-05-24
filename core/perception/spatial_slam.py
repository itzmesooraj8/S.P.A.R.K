from __future__ import annotations

import numpy as np
import open3d as o3d
import threading
import time

class AsyncSpatialSLAM:
    """Asynchronous SLAM and point-cloud feature mapping using Open3D reconstruction."""
    def __init__(self):
        self.point_cloud = o3d.geometry.PointCloud()
        self.mesh = o3d.geometry.TriangleMesh()
        self.lock = threading.Lock()
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()

    def add_depth_points(self, rgb_frame: np.ndarray, depth_map: np.ndarray, intrinsic_matrix: np.ndarray):
        # Ingest depth values, project into 3D coordinate space
        h, w = depth_map.shape
        fx, fy = intrinsic_matrix[0, 0], intrinsic_matrix[1, 1]
        cx, cy = intrinsic_matrix[0, 2], intrinsic_matrix[1, 2]
        
        x_indices, y_indices = np.meshgrid(np.arange(w), np.arange(h))
        z = depth_map.astype(np.float32) / 1000.0  # convert from millimeters to meters
        x = (x_indices - cx) * z / fx
        y = (y_indices - cy) * z / fy
        
        valid_mask = z > 0.1  # ignore near-range noise
        points = np.stack((x[valid_mask], y[valid_mask], z[valid_mask]), axis=-1)
        colors = rgb_frame[valid_mask].astype(np.float32) / 255.0

        with self.lock:
            new_pcd = o3d.geometry.PointCloud()
            new_pcd.points = o3d.utility.Vector3dVector(points)
            new_pcd.colors = o3d.utility.Vector3dVector(colors)
            self.point_cloud += new_pcd
            self.point_cloud = self.point_cloud.voxel_down_sample(voxel_size=0.02)

    def _process_loop(self):
        while self._running:
            time.sleep(0.5)
            with self.lock:
                if len(self.point_cloud.points) < 50:
                    continue
                # Normal estimation
                self.point_cloud.estimate_normals(
                    search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30)
                )
                self.point_cloud.orient_normals_towards_camera_location(camera_location=np.zeros(3))
                
                # Ball Pivoting Algorithm mesh generation
                distances = self.point_cloud.compute_nearest_neighbor_distance()
                if len(distances) == 0:
                    continue
                avg_dist = np.mean(distances)
                radii = [avg_dist, 2 * avg_dist]
                
                try:
                    self.mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(
                        self.point_cloud, o3d.utility.DoubleVector(radii)
                    )
                except Exception:
                    pass

    def get_mesh_vertices_count(self) -> int:
        with self.lock:
            return len(self.mesh.vertices)

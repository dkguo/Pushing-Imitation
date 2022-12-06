import json

import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation

def load_time(time_file_path):
    with open(time_file_path) as f:
        return json.load(f).values()


def load_object_poses(file_path):
    """
    This function loads object poses assuming there is only one identical object in each frame.
    :param file_path: the file has dict[frame][object_id] = pose

    :return: object_poses: dict[object_id] = pose
    """
    with open(file_path) as f:
        frame_object_poses = json.load(f)

    # find obj keys
    obj_ids = set()
    for object_poses in frame_object_poses.values():
        for obj_id in object_poses.keys():
            obj_ids.add(obj_id)

    object_poses = {}
    for obj_id in obj_ids:
        poses = []
        last_frame = int(list(frame_object_poses.keys())[-1])
        for frame in range(last_frame + 1):
            if str(frame) in frame_object_poses:
                if obj_id in frame_object_poses[str(frame)]:
                    pose = np.array(frame_object_poses[str(frame)][obj_id])
                    assert pose.shape == (4, 4)
                    poses.append(np.array(frame_object_poses[str(frame)][obj_id]))
                else:
                    poses.append(None)
            else:
                poses.append(None)
        object_poses[obj_id] = poses

    return object_poses


def kalman_filter(poses, dt=1/30, P0=500.0, sq_sigma_a=100, r=1.0):
    """
    Apply linear kalman filter on poses.
    Poses are converted to position and euler angles: [x y z ex ey ez]
    :param poses: list of pose in homogenous matrix from frame 0 to end
    :param dt: delta time between two frames
    :param P0: initial uncertainty of the first state
    :param sq_sigma_a: random variance in acceleration
    :param r: measurement uncertainty

    :return zs: estimated poses
    """
    # poses to positions and euler angles
    positions = []
    angles = []
    for i, pose in enumerate(poses):
        if pose is not None:
            positions.append(pose[:3, -1])
            # print(Rotation.from_matrix(pose[:3, :3]).as_euler('XYZ'))
            angles.append(Rotation.from_matrix(pose[:3, :3]).as_euler('XYZ'))
        else:
            positions.append(np.array([np.nan, np.nan, np.nan]))
            angles.append(np.array([np.nan, np.nan, np.nan]))
    positions = np.array(positions)
    angles = np.array(angles)

    # add ±2pi if diff from last point more than 1.8pi
    not_nan_angles = angles[~np.isnan(angles)].reshape((-1, 3))
    for i in range(1, len(not_nan_angles)):
        for j in range(len(not_nan_angles[0])):
            if not_nan_angles[i][j] - not_nan_angles[i - 1][j] > 1.8 * np.pi:
                not_nan_angles[i][j] -= 2 * np.pi
            elif not_nan_angles[i][j] - not_nan_angles[i - 1][j] < -1.8 * np.pi:
                not_nan_angles[i][j] += 2 * np.pi
    angles[~np.isnan(angles)] = not_nan_angles.reshape((-1))
    # plt.plot(angles[:, 0], '-o')
    # plt.plot(angles[:, 1], '-o')
    # plt.plot(angles[:, 2], '-o')
    # plt.show()

    # remove nan at the begining and in the end
    not_nan_frames = np.nonzero(~np.isnan(positions[:, 0]))
    positions = positions[np.min(not_nan_frames):np.max(not_nan_frames) + 1]
    angles = angles[np.min(not_nan_frames):np.max(not_nan_frames) + 1]

    # create variables
    n = len(positions)
    x = [[None] * n] * (n + 1)
    P = [[None] * n] * (n + 1)
    K = [None] * n
    z = [None] * n

    # state transition matrix F
    F = np.array([[1, dt, 0.5 * dt ** 2],
                  [0,  1,            dt],
                  [0,  0,             1]])
    F = np.kron(np.eye(6), F)

    # process noise Q
    Q = np.array([[dt ** 4 / 4, dt ** 3 / 2, dt ** 2 / 2],
                  [dt ** 3 / 2,     dt ** 2,          dt],
                  [dt ** 2 / 2,          dt,           1]])
    Q = np.kron(np.eye(6), Q) * sq_sigma_a

    # observation matrix H, z = H @ x + v
    H = np.zeros([6, 18])
    for i in range(6):
        H[i, 3 * i] = 1

    # measurement uncertainty
    R = np.diag([r] * 6)

    # state x initialization
    x0 = np.zeros(18)
    x0[np.arange(0, 9, 3)] = positions[0]
    x0[np.arange(9, 18, 3)] = angles[0]
    x[0][0] = x0

    # uncertainty P initializaiton
    P[0][0] = np.kron(np.eye(6), np.full((3, 3), P0))

    # first step
    x[1][0] = F @ x[0][0]
    P[1][0] = F @ P[0][0] @ F.T + Q

    # apply Kalman filter
    for i in range(1, n):
        z[i] = np.r_[positions[i], angles[i]]

        K[i] = (P[i][i - 1] @ H.T) @ np.linalg.pinv(H @ P[i][i - 1] @ H.T + R)
        x[i][i] = x[i][i - 1] + K[i] @ (z[i] - H @ x[i][i - 1])
        P[i][i] = (np.eye(9) - K[i] @ H) @ P[i][i - 1] @ (np.eye(9) - K[i] @ H).T + K[i] @ R @ K[i].T

        x[i + 1][i] = F @ x[i][i]
        P[i + 1][i] = F @ P[i][i] @ F.T + Q

    # get estimated states
    est_z = np.zeros()


def kalman_filter_constant_acc(zs, dt=1/30, P0=500.0, sq_sigma_a=100, r=1.0):
    """
    Apply linear kalman filter on measurements.
    Measurements are independent.
    :param zs: list of measurements, (n, d), cannot start or end with nan
    :param dt: delta time between two frames
    :param P0: initial uncertainty of the first state
    :param sq_sigma_a: random variance in acceleration
    :param r: measurement uncertainty

    :return est_zs: estimated values after applying Kalman filter
    """

    pass


def plot_poses(poses):
    coods = []
    for pose in poses[:100]:
        if pose is not None:
            p_object = pose[:3, 3]
            R = pose[:3, :3]
            p_x = R @ [0.01, 0, 0]
            p_y = R @ [0, 0.01, 0]
            p_z = R @ [0, 0, 0.01]
            cood = np.r_[[np.r_[p_object, p_x],
                          np.r_[p_object, p_y],
                          np.r_[p_object, p_z]]]
            coods.append(cood)

    coods = np.array(coods)

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    for i, c in zip(range(3), ['b', 'r', 'g']):
        s = coods[:, i, :].reshape((-1, 6))
        X, Y, Z, U, V, W = zip(*s)
        ax.quiver(X, Y, Z, U, V, W, color=c)
    plt.show()


if __name__ == '__main__':
    times = load_time('./time.json')
    object_poses = load_object_poses('./object_poses.json')

    object_est_poses = {}
    poses = object_poses['13']
    for i in range(len(poses)):
        if poses[i] is not None:
            first_none = i
    for i in range(len(poses)):
        if poses[i] is not None:
            poses[i] = np.linalg.inv(poses[first_none]) @ poses[i]
    # for object_id, poses in object_poses.items():
    # plot_poses(poses)
    filtered_poses = kalman_filter(poses)
        # object_est_poses[object_id] = kalman_filter(times, poses)

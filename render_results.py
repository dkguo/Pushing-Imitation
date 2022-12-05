import json

import numpy as np

import mengine as m
from recover_push import reset, get_robot_contact_pt, simulate_one_step, scenario

EXE_SEED = 32


if __name__ == '__main__':
    # init_globals()
    exe_env = m.Env(render=True)
    orient = m.get_quaternion([np.pi, 0, 0])
    exe_env.seed(EXE_SEED)
    exe_robot, exe_cube, exe_true_cube = reset(
        exe_env,
        scenario['position'],
        scenario['table_friction'],
        scenario['cube_mass'],
        scenario['cube_friction'],
    )

    # Load results
    with open('results.json') as f:
        results = json.load(f)

    all_robot_pts, desire_cube_poses, all_forces = \
        results['all_robot_pts'], results['desire_cube_poses'], results['all_forces']

    all_robot_pts = np.array(all_robot_pts)
    all_forces = np.array(all_forces)
    desire_cube_poses = np.array(desire_cube_poses)

    # set exe_robot to somewhere near the first pose
    robot_pt = get_robot_contact_pt(
        [desire_cube_poses[0]],
        x_offset=0.5,
    )[0][:3, -1]
    cube_pose, robot_joint_angles = simulate_one_step(
        'EXECUTE',
        robot_pt,
        force=100,
        desire_cube_pose=desire_cube_poses[0],
        exe_env=exe_env,
        exe_cube=exe_cube,
        exe_robot=exe_robot,
        exe_true_cube=exe_true_cube
    )

    for robot_pt, force, desire_cube_pose in zip(all_robot_pts, all_forces, desire_cube_poses):
        simulate_one_step(
            'EXECUTE',
            robot_pt,
            force,
            desire_cube_pose=desire_cube_pose,
            exe_env=exe_env,
            exe_cube=exe_cube,
            exe_robot=exe_robot,
            exe_true_cube=exe_true_cube
        )

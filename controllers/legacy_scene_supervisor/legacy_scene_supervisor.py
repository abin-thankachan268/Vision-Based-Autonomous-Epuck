from controller import Supervisor
import math
import csv

class SceneSupervisor(Supervisor):
    def __init__(self):
        super().__init__()
        self.time_step = int(self.getBasicTimeStep())
        if self.time_step <= 0:
            self.time_step = 32
        # Device used to broadcast distances to the robot
        self.emitter = self.getDevice("dist_emitter")
        # -------- Parameters --------
        self.MOVE_DELAY = 5.0      # movement starts after 5 seconds
        self.PED_AMP   = 0.3       # PED y oscillation amplitude
        self.PED_SPEED = 0.6       # PED oscillation speed (0.4 * 1.5 = 0.6 for 1.5x faster)
        # -------- Get nodes --------
        self.ped_node   = self.getFromDef("ped")
        self.obs_node   = self.getFromDef("obs")
        self.robot_node = self.getFromDef("EPUCK")
        self.ped_translation   = self.ped_node.getField("translation")
        self.obs_translation   = self.obs_node.getField("translation")
        self.robot_translation = self.robot_node.getField("translation")
        # Save starting positions
        self.ped_start   = self.ped_translation.getSFVec3f()
        self.obs_start   = self.obs_translation.getSFVec3f()   # BLUE stays static
        self.robot_start = self.robot_translation.getSFVec3f()
        # -------- CSV Logging --------
        self.log_file = open("distance_log.csv", "w", newline="")
        self.csv_writer = csv.writer(self.log_file)
        self.csv_writer.writerow([
            "time_s",
            "ped_x", "ped_y", "ped_z",
            "obs_x", "obs_y", "obs_z",
            "robot_x", "robot_y", "robot_z",
            "dist_robot_ped", "dist_robot_obs"
        ])
        print("[Supervisor] Logging enabled. Delay =", self.MOVE_DELAY)
        print("[Supervisor] Pedestrian moving along Y-AXIS")
    
    def run(self):
        while self.step(self.time_step) != -1:
            t = self.getTime()
            # Robot position (never moved)
            robot_pos = self.robot_translation.getSFVec3f()
            robot_x, robot_y, robot_z = robot_pos
            # Default positions before delay
            ped_x, ped_y, ped_z = self.ped_start
            obs_x, obs_y, obs_z = self.obs_start    # static blue obstacle
            # ------------ Delay logic -------------
            if t >= self.MOVE_DELAY:
                td = t - self.MOVE_DELAY
                # ---- Move ONLY PED along Y-axis ----
                ped_x = self.ped_start[0]
                ped_y = self.ped_start[1] + self.PED_AMP * math.sin(self.PED_SPEED * td)
                ped_z = self.ped_start[2]
                self.ped_translation.setSFVec3f([ped_x, ped_y, ped_z])
                # ---- BLUE OBSTACLE DOES NOT MOVE ----
                self.obs_translation.setSFVec3f(self.obs_start)
            else:
                # Before delay → freeze both at start positions
                self.ped_translation.setSFVec3f(self.ped_start)
                self.obs_translation.setSFVec3f(self.obs_start)
            # ------------ Distance calculation (3D) -------------
            dist_robot_ped = math.sqrt((robot_x - ped_x)**2 + (robot_y - ped_y)**2 + (robot_z - ped_z)**2)
            dist_robot_obs = math.sqrt((robot_x - obs_x)**2 + (robot_y - obs_y)**2 + (robot_z - obs_z)**2)
            # ------------ Log to CSV -------------
            self.csv_writer.writerow([
                f"{t:.3f}",
                f"{ped_x:.4f}", f"{ped_y:.4f}", f"{ped_z:.4f}",
                f"{obs_x:.4f}", f"{obs_y:.4f}", f"{obs_z:.4f}",
                f"{robot_x:.4f}", f"{robot_y:.4f}", f"{robot_z:.4f}",
                f"{dist_robot_ped:.4f}", f"{dist_robot_obs:.4f}"
            ])
            # ------------ Broadcast distances to the E-puck -------------
            if self.emitter is not None:
                payload = f"{t:.3f},{dist_robot_ped:.4f},{dist_robot_obs:.4f}"
                self.emitter.send(payload.encode("utf-8"))
        self.log_file.close()
        print("[Supervisor] Log file closed.")

# MAIN
if __name__ == "__main__":
    controller = SceneSupervisor()
    controller.run()

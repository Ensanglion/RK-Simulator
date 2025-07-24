import pygame
import os
import sys
import numpy as np
from PIL import Image
import math
import random

global music_started
music_started = False
knight_trail = []
trail_length = 10
trail_alphas = [80, 70, 60, 50, 40, 30, 20, 15, 10, 5]

OUTLINE_COLOR = (39, 41, 63, 255)  # RGBA for outline

def main():
    pygame.init()
    pygame.mixer.init()

    # Get user's screen size
    info = pygame.display.Info()
    screen_width, screen_height = info.current_w, info.current_h
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
    pygame.display.set_caption("Fountain Animation")

    # Paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bg_path = os.path.join(base_dir, 'sprites', 'spr_knight_snow_bg.png')
    fountain_dir = os.path.join(base_dir, 'sprites', 'spr_fountainbg')
    fountain_files = [
        os.path.join(fountain_dir, f'spr_cc_fountainbg_{i}.png') for i in range(4)
    ]
    fountain_frames = [pygame.image.load(f).convert_alpha() for f in fountain_files]
    # Scale fountain frames to width 600px, keep aspect ratio
    fountain_width = 600
    orig_w, orig_h = fountain_frames[0].get_width(), fountain_frames[0].get_height()
    scale_factor = fountain_width / orig_w
    fountain_scaled_frames = [
        pygame.transform.smoothscale(frame, (fountain_width, int(orig_h * scale_factor)))
        for frame in fountain_frames
    ]
    fountain_frame_count = 4
    fountain_frame_idx = 0
    fountain_anim_speed = 16  # frames per sprite 
    fountain_anim_timer = 0

    # Load and scale background
    bg_img = pygame.image.load(bg_path).convert()
    bg_img = pygame.transform.scale(bg_img, (screen_width, screen_height))

    # Animation setup
    order = [0, 1, 2, 3]
    clock = pygame.time.Clock()
    running = True
    frame_count = 0
    swap_interval = 15  # frames between swaps (adjust for speed)
    current_idx = 0

    # Helper to extract outline rows from a surface
    def get_outline_rows(surf):
        arr = pygame.surfarray.pixels_alpha(surf)
        w, h = surf.get_width(), surf.get_height()
        surf_rgba = pygame.surfarray.pixels3d(surf)
        # Find top and bottom outline rows
        def row_rgba(y):
            return [tuple(surf_rgba[x, y]) + (arr[x, y],) for x in range(w)]
        # Top outline row
        for top_y in range(h):
            row = row_rgba(top_y)
            if OUTLINE_COLOR in row:
                break
        # Bottom outline row
        for bottom_y in range(h - 1, -1, -1):
            row = row_rgba(bottom_y)
            if OUTLINE_COLOR in row:
                break
        return row_rgba(top_y), row_rgba(bottom_y), top_y, bottom_y

    # Precompute outline rows for all frames
    fountain_outlines = []
    for surf in fountain_scaled_frames:
        top_row, bottom_row, top_y, bottom_y = get_outline_rows(surf)
        fountain_outlines.append({
            'top_row': top_row,
            'bottom_row': bottom_row,
            'top_y': top_y,
            'bottom_y': bottom_y
        })

    # Convert each image to a 2D array of RGBA values (height x width x 4)
    def surf_to_rgba_array(surf):
        arr_rgb = pygame.surfarray.array3d(surf)  # shape: (w, h, 3)
        arr_alpha = pygame.surfarray.array_alpha(surf)  # shape: (w, h)
        arr_rgba = np.zeros((surf.get_height(), surf.get_width(), 4), dtype=np.uint8)
        arr_rgba[:, :, :3] = np.transpose(arr_rgb, (1, 0, 2))
        arr_rgba[:, :, 3] = np.transpose(arr_alpha, (1, 0))
        return arr_rgba

    fountain_arrays = [surf_to_rgba_array(surf) for surf in fountain_scaled_frames]

    # Helper to find best matching row in next image for alignment
    def find_best_row_match(top_row, arr_next):
        h, w, _ = arr_next.shape
        min_diff = float('inf')
        best_row = h - 1
        for y in range(h - 1, -1, -1):
            row = arr_next[y]
            diff = np.sum(np.abs(row.astype(int) - top_row.astype(int)))
            if diff < min_diff:
                min_diff = diff
                best_row = y
                if diff == 0:
                    break  # exact match
        return best_row

    # Function to combine 2 images in a given order, aligning by best row match
    def combine_fountain_stack(order, arrays, surfs):
        base_idx = order[0]
        base_arr = arrays[base_idx]
        h, w, _ = base_arr.shape
        offsets = [0]
        curr_y = 0
        curr_top_row = base_arr[0]
        total_height = h
        for i in range(1, 2):
            next_idx = order[i]
            next_arr = arrays[next_idx]
            best_row = find_best_row_match(curr_top_row, next_arr)
            offsets.append(curr_y - best_row)
            curr_y = curr_y - best_row + h
            curr_top_row = next_arr[0]
            total_height = curr_y
        combined_surf = pygame.Surface((w, total_height), pygame.SRCALPHA)
        for i in range(2):
            idx = order[i]
            surf = surfs[idx]
            y_offset = offsets[i]
            combined_surf.blit(surf, (0, y_offset))
        return combined_surf

    # Precompute the 4 combined images (using 2 images per frame)
    combined_orders = [
        [0, 1],
        [1, 2],
        [2, 3],
        [3, 0],
    ]
    combined_fountain_surfs = [
        combine_fountain_stack(order, fountain_arrays, fountain_scaled_frames) for order in combined_orders
    ]

    # Load Kris's idle animation frames
    kris_idle_dir = os.path.join(base_dir, 'sprites', 'spr_krisb_idle')
    kris_idle_files = sorted([
        os.path.join(kris_idle_dir, f) for f in os.listdir(kris_idle_dir)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ])
    kris_base_img = pygame.image.load(kris_idle_files[0]).convert_alpha()
    kris_base_size = kris_base_img.get_size()
    kris_target_size = (kris_base_size[0] * 3, kris_base_size[1] * 3)
    kris_idle_frames = [pygame.transform.smoothscale(pygame.image.load(f).convert_alpha(), kris_target_size) for f in kris_idle_files]
    kris_frame_count = len(kris_idle_frames)
    kris_frame_idx = 0
    kris_anim_speed = 8  # frames per sprite
    kris_anim_timer = 0

    # Load Susie's idle animation frames
    susie_idle_dir = os.path.join(base_dir, 'sprites', 'spr_susieb_idle')
    susie_idle_files = sorted([
        os.path.join(susie_idle_dir, f) for f in os.listdir(susie_idle_dir)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ])
    susie_base_img = pygame.image.load(susie_idle_files[0]).convert_alpha()
    susie_base_size = susie_base_img.get_size()
    susie_target_size = (susie_base_size[0] * 3, susie_base_size[1] * 3)
    susie_idle_frames = [pygame.transform.smoothscale(pygame.image.load(f).convert_alpha(), susie_target_size) for f in susie_idle_files]
    susie_frame_count = len(susie_idle_frames)
    susie_frame_idx = 0
    susie_anim_speed = 8  # frames per sprite
    susie_anim_timer = 0

    # Load Ralsei's idle animation frames
    ralsei_idle_dir = os.path.join(base_dir, 'sprites', 'spr_ralsei_idle')
    ralsei_idle_files = sorted([
        os.path.join(ralsei_idle_dir, f) for f in os.listdir(ralsei_idle_dir)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ])
    ralsei_idle_orig = pygame.image.load(ralsei_idle_files[0]).convert_alpha()
    ralsei_target_size = (int(ralsei_idle_orig.get_width() * 3), int(ralsei_idle_orig.get_height() * 3))
    ralsei_idle_frames = [pygame.transform.smoothscale(pygame.image.load(f).convert_alpha(), ralsei_target_size) for f in ralsei_idle_files]
    ralsei_frame_count = len(ralsei_idle_frames)
    ralsei_frame_idx = 0
    ralsei_anim_speed = 8  # frames per sprite
    ralsei_anim_timer = 0

    # Battle box setup
    battle_box_width = 450
    battle_box_height = 300
    battle_box_border = 4
    battle_box_color = (0, 0, 0)
    battle_box_border_color = (0, 255, 0)
    battle_box_rect = pygame.Rect(
        (screen_width - battle_box_width) // 2 + 50,
        (screen_height - battle_box_height) // 2 + 20,
        battle_box_width,
        battle_box_height
    )
    original_battle_box_rect = battle_box_rect.copy()

    # Load knight idle sprite
    knight_idle_img = pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_roaringknight_idle.png')).convert_alpha()
    knight_idle_img = pygame.transform.smoothscale(knight_idle_img, (int(knight_idle_img.get_width() * 3), int(knight_idle_img.get_height() * 3)))
    # Load heart sprite
    heart_size = 32  # scale heart to 32x32 px
    heart_img_0 = pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_heart', 'spr_heart_0.png')).convert_alpha()
    heart_img_0 = pygame.transform.smoothscale(heart_img_0, (heart_size, heart_size))
    heart_img_1 = pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_heart', 'spr_heart_1.png')).convert_alpha()
    heart_img_1 = pygame.transform.smoothscale(heart_img_1, (heart_size, heart_size))
    heart_img = heart_img_0
    knight_trail = []
    trail_length = 10
    trail_alphas = [80, 70, 60, 50, 40, 30, 20, 15, 10, 5]
    invincible_until = 0
    # Player position (center of battle box)
    player_x = battle_box_rect.left + battle_box_width // 2 - heart_size // 2
    player_y = battle_box_rect.top + battle_box_height // 2 - heart_size // 2
    player_speed = 5

    # Kris
    kris_img = kris_idle_frames[0]
    kris_rect = kris_img.get_rect()
    kris_rect.left = 350
    kris_rect.centery = screen_height // 2 - 100 

    # Susie
    susie_img = susie_idle_frames[0]
    susie_rect = susie_img.get_rect()
    susie_rect.left = kris_rect.left - 120
    susie_rect.centery = kris_rect.centery + 100

    # Ralsei
    ralsei_img = ralsei_idle_frames[0]
    ralsei_rect = ralsei_img.get_rect()
    ralsei_rect.left = susie_rect.left - 10
    ralsei_rect.centery = susie_rect.centery + 100

    font = pygame.font.SysFont(None, 48)

    player_lives = 999

    # Call the intro cutscene before the main loop
    player_x, player_y = play_battle_intro(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_idle_frames, kris_rect, susie_idle_frames, susie_rect,
        ralsei_idle_frames, ralsei_rect, battle_box_rect, base_dir,
        kris_target_size, susie_target_size, ralsei_target_size,
        kris_frame_idx, susie_frame_idx, ralsei_frame_idx,
        battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives,
        fountain_anim_speed, fountain_frame_count,
        kris_anim_speed, kris_frame_count,
        susie_anim_speed, susie_frame_count,
        ralsei_anim_speed, ralsei_frame_count,
        fountain_anim_timer, kris_anim_timer, susie_anim_timer, ralsei_anim_timer
    )

    knight_point_trail = []  # Trail for the pointing Knight
    
    # Start Attack 1
    knight_point_img, knight_point_rect, knight_point_frames, player_x, player_y, \
    triangle_knight_img, triangle_knight_rect, triangle_start_time, knight_reverse_duration, knight_idle_img, \
    fountain_frame_idx, kris_frame_idx, susie_frame_idx, ralsei_frame_idx, \
    fountain_anim_timer, kris_anim_timer, susie_anim_timer, ralsei_anim_timer = PreAttack1(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_rect, battle_box_rect, knight_idle_img, clock,
        battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        player_speed=player_speed
    )

    # Start Attack 1 (call Attack1 with all required arguments)
    attack1 = Attack1(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives,
        knight_point_img, knight_point_rect, knight_point_frames,
        clock, player_speed,
        screen_height, base_dir, knight_point_trail,
        fountain_anim_speed, fountain_frame_count,
        kris_anim_speed, kris_frame_count,
        susie_anim_speed, susie_frame_count,
        ralsei_anim_speed, ralsei_frame_count,
        fountain_anim_timer, kris_anim_timer, susie_anim_timer, ralsei_anim_timer,
        invincible_until,
        triangle_start_time, triangle_knight_img, triangle_knight_rect, knight_reverse_duration, knight_idle_img
    )
    attack1.run()
    player_lives = attack1.player_lives

    # After Attack1(), before PreAttack2(), clear the screen with the background
    bg_img_scaled = pygame.transform.scale(bg_img, (screen.get_width(), screen.get_height()))
    screen.blit(bg_img_scaled, (0, 0))
    pygame.display.flip()

    invincible = False
    show_knight_idle = True
    knight_idle_left = battle_box_rect.right + 40
    knight_idle_centery = kris_rect.centery + 20
    battle_box_rect, player_x, player_y = PreAttack2(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        battle_box_rect, original_battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
        knight_idle_img, show_knight_idle, clock,
        knight_idle_left, knight_idle_centery,
        anim_duration=2000, player_speed=player_speed
    )

    # --- Start Attack2 ---
    attack2 = Attack2(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives,
        clock, player_speed, base_dir, knight_idle_img,
        fountain_anim_speed=16, fountain_frame_count=4,
        kris_anim_speed=8, kris_frame_count=None,
        susie_anim_speed=8, susie_frame_count=None,
                 ralsei_anim_speed=8, ralsei_frame_count=None, show_wheel=False
    )
    attack2.run()
    player_lives = attack2.player_lives

    # After Attack2(), before PreAttack3(), clear the screen with the background
    bg_img_scaled = pygame.transform.scale(bg_img, (screen.get_width(), screen.get_height()))
    screen.blit(bg_img_scaled, (0, 0))
    pygame.display.flip()

    battle_box_rect, player_x, player_y = PreAttack3(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
        knight_idle_img, show_knight_idle, clock,
        anim_duration=2000, player_speed=player_speed
    )

    # --- Start Attack3 ---
    attack3 = Attack3(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
        knight_idle_img, show_knight_idle, clock,
        knight_trail, trail_length, trail_alphas,
        cut_mode='vertical', cycles=7, player_speed=player_speed
    )
    attack3.run()
    player_lives = attack3.player_lives

    # 0.5 second of idle animation before Attack4
    idle_start = pygame.time.get_ticks()
    while pygame.time.get_ticks() - idle_start < 500:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                sys.exit()
        draw_main_scene(
            screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
            kris_idle_frames, kris_frame_idx, kris_rect,
            susie_idle_frames, susie_frame_idx, susie_rect,
            ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
            battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, False,
            knight_idle_img, show_knight_idle, clock
        )
        pygame.display.flip()
        clock.tick(60)

    # --- Attack4 here ---
    # Setup for Attack4: knight goes through the pointing animation (PreAttack1)
    knight_point_img, knight_point_rect, knight_point_frames, player_x, player_y, \
    triangle_knight_img, triangle_knight_rect, triangle_start_time, knight_reverse_duration, knight_idle_img, \
    fountain_frame_idx, kris_frame_idx, susie_frame_idx, ralsei_frame_idx, \
    fountain_anim_timer, kris_anim_timer, susie_anim_timer, ralsei_anim_timer = PreAttack1(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_rect, battle_box_rect, knight_idle_img, clock,
        battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        player_speed=player_speed
    )

    # --- Start Attack4 ---
    attack4 = Attack4(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
        knight_idle_img, show_knight_idle, clock,
        base_dir=base_dir, player_speed=player_speed
    )
    attack4.run()
    player_lives = attack4.player_lives

    # After Attack4(), before Attack5(), clear the screen with the background
    bg_img_scaled = pygame.transform.scale(bg_img, (screen.get_width(), screen.get_height()))
    screen.blit(bg_img_scaled, (0, 0))
    pygame.display.flip()

    # --- Attack5: Spinning Slash ---
    battle_box_rect, player_x, player_y = PreAttack5(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
        knight_idle_img, show_knight_idle, clock,
        anim_duration=2000, player_speed=player_speed
    )

    attack5 = Attack5(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
        knight_idle_img, show_knight_idle, clock,
        base_dir=base_dir, player_speed=player_speed
    )
    attack5.run()
    player_lives = attack5.player_lives

    # After Attack5(), before Attack6(), clear the screen with the background
    bg_img_scaled = pygame.transform.scale(bg_img, (screen.get_width(), screen.get_height()))
    screen.blit(bg_img_scaled, (0, 0))
    pygame.display.flip()

    # Reset battle box to default size before Attack6 (same logic as before Attack3)
    battle_box_rect, player_x, player_y = PreAttack3(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
        knight_idle_img, show_knight_idle, clock,
        anim_duration=2000, player_speed=player_speed
    )

    # --- Attack6: Attack1 with 20% larger starchilds ---
    # Setup for Attack6: knight goes through the pointing animation (PreAttack1)
    knight_point_img, knight_point_rect, knight_point_frames, player_x, player_y, \
    triangle_knight_img, triangle_knight_rect, triangle_start_time, knight_reverse_duration, knight_idle_img, \
    fountain_frame_idx, kris_frame_idx, susie_frame_idx, ralsei_frame_idx, \
    fountain_anim_timer, kris_anim_timer, susie_anim_timer, ralsei_anim_timer = PreAttack1(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_rect, battle_box_rect, knight_idle_img, clock,
        battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        player_speed=player_speed
    )

    attack6 = Attack1(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives,
        knight_point_img, knight_point_rect, knight_point_frames,
        clock, player_speed,
        screen_height, base_dir, knight_point_trail,
        fountain_anim_speed, fountain_frame_count,
        kris_anim_speed, kris_frame_count,
        susie_anim_speed, susie_frame_count,
        ralsei_anim_speed, ralsei_frame_count,
        fountain_anim_timer, kris_anim_timer, susie_anim_timer, ralsei_anim_timer,
        invincible_until,
        triangle_start_time, triangle_knight_img, triangle_knight_rect, knight_reverse_duration, knight_idle_img,
        starchild_scale=1.2
    )
    attack6.run()
    player_lives = attack6.player_lives

    # After Attack6(), before Attack7(), clear the screen with the background
    bg_img_scaled = pygame.transform.scale(bg_img, (screen.get_width(), screen.get_height()))
    screen.blit(bg_img_scaled, (0, 0))
    pygame.display.flip()

    # --- Attack7: Random Cut Attack ---
    attack7 = Attack7(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
        knight_idle_img, show_knight_idle, clock,
        knight_trail, trail_length, trail_alphas,
        cycles=7, base_dir=base_dir, player_speed=player_speed
    )
    attack7.run()
    player_lives = attack7.attack3.player_lives

    # After Attack7(), before PreAttack2(), clear the screen with the background
    bg_img_scaled = pygame.transform.scale(bg_img, (screen.get_width(), screen.get_height()))
    screen.blit(bg_img_scaled, (0, 0))
    pygame.display.flip()

    invincible = False
    show_knight_idle = True
    knight_idle_left = battle_box_rect.right + 40
    knight_idle_centery = kris_rect.centery + 20
    battle_box_rect, player_x, player_y = PreAttack2(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        battle_box_rect, original_battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
        knight_idle_img, show_knight_idle, clock,
        knight_idle_left, knight_idle_centery,
        anim_duration=2000, player_speed=player_speed
    )

    # --- Attack8: Sword Wheel ---
    attack8 = Attack8(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives,
        clock, 5, base_dir, knight_idle_img,
        show_wheel=True
    )
    attack8.run()
    player_lives = attack8.player_lives

    # After Attack8(), before Attack9(), clear the screen with the background
    bg_img_scaled = pygame.transform.scale(bg_img, (screen.get_width(), screen.get_height()))
    screen.blit(bg_img_scaled, (0, 0))
    pygame.display.flip()

# 0.5 second of idle animation before Attack4
    idle_start = pygame.time.get_ticks()
    while pygame.time.get_ticks() - idle_start < 500:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                sys.exit()
        draw_main_scene(
            screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
            kris_idle_frames, kris_frame_idx, kris_rect,
            susie_idle_frames, susie_frame_idx, susie_rect,
            ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
            battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, False,
            knight_idle_img, show_knight_idle, clock
        )
        pygame.display.flip()
        clock.tick(60)

    # Define Attack9 sequences (all using the last slash from Attack5)
    attack9_sequences = [
        ('spr_rk_spinslash4_red.png', 'spr_rk_spinslash4.png'),
        ('spr_rk_spinslash4_red.png', 'spr_rk_spinslash4.png'),
        ('spr_rk_spinslash4_red.png', 'spr_rk_spinslash4.png'),
        ('spr_rk_spinslash4_red.png', 'spr_rk_spinslash4.png'),
        ('spr_rk_spinslash4_red.png', 'spr_rk_spinslash4.png')
    ]

    attack9 = Attack5(  # Reusing the same Attack5 class
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
        knight_idle_img, show_knight_idle, clock,
        base_dir=base_dir, player_speed=player_speed,
        sequences=attack9_sequences  # Pass the custom sequences here
    )
    attack9.run()
    player_lives = attack9.player_lives

    # After Attack9(), before Attack10(), clear the screen with the background
    bg_img_scaled = pygame.transform.scale(bg_img, (screen.get_width(), screen.get_height()))
    screen.blit(bg_img_scaled, (0, 0))
    pygame.display.flip()

    # 0.5 second of idle animation before Attack4
    idle_start = pygame.time.get_ticks()
    while pygame.time.get_ticks() - idle_start < 500:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                sys.exit()
        draw_main_scene(
            screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
            kris_idle_frames, kris_frame_idx, kris_rect,
            susie_idle_frames, susie_frame_idx, susie_rect,
            ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
            battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, False,
            knight_idle_img, show_knight_idle, clock
        )
        pygame.display.flip()
        clock.tick(60)

    # --- Attack10: Slash Wheel ---
    attack10 = Attack10(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
        knight_idle_img, show_knight_idle, clock,
        base_dir=base_dir, player_speed=player_speed
    )
    attack10.run()
    player_lives = attack10.player_lives

    # --- Final Attack Sequence ---
    final_attack = FinalAttackSequence(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
        knight_idle_img, show_knight_idle, clock,
        base_dir=base_dir, player_speed=player_speed
    )
    final_attack.run()

    pygame.quit()
    sys.exit()



def play_battle_intro(screen, bg_img, fountain_scaled_frames, fountain_frame_idx, kris_idle_frames, kris_rect, susie_idle_frames, susie_rect, ralsei_idle_frames, ralsei_rect, battle_box_rect, base_dir, kris_target_size, susie_target_size, ralsei_target_size, kris_frame_idx, susie_frame_idx, ralsei_frame_idx, battle_box_color, battle_box_border_color, battle_box_border, heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, fountain_anim_speed, fountain_frame_count, kris_anim_speed, kris_frame_count, susie_anim_speed, susie_frame_count, ralsei_anim_speed, ralsei_frame_count, fountain_anim_timer, kris_anim_timer, susie_anim_timer, ralsei_anim_timer):
    # Load intro animations
    def load_anim(folder, numeric_sort=False):
        files = [
            os.path.join(folder, f) for f in os.listdir(folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]
        if numeric_sort:
            files.sort(key=lambda x: int(''.join(filter(str.isdigit, os.path.basename(x))) or 0))
        else:
            files = sorted(files)
        return [pygame.image.load(f).convert_alpha() for f in files]

    kris_intro_frames = load_anim(os.path.join(base_dir, 'sprites', 'spr_krisb_intro'))
    susie_intro_frames = load_anim(os.path.join(base_dir, 'sprites', 'spr_susieb_attack'))
    ralsei_intro_frames = load_anim(os.path.join(base_dir, 'sprites', 'spr_ralsei_battleintro'))
    knight_intro_frames = load_anim(os.path.join(base_dir, 'sprites', 'spr_roaringknight_sword_appear_new'), numeric_sort=True)
    knight_idle_img = pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_roaringknight_idle.png')).convert_alpha()

    # Scale all intro frames to match idle frame sizes
    def scale_all_to_target(frames, target_size):
        return [pygame.transform.smoothscale(f, target_size) for f in frames]

    # Kris
    kris_intro_frames = scale_all_to_target(kris_intro_frames, kris_target_size)
    kris_idle_frames = scale_all_to_target(kris_idle_frames, kris_target_size)
    # Susie
    susie_intro_frames = scale_all_to_target(susie_intro_frames, susie_target_size)
    susie_idle_frames = scale_all_to_target(susie_idle_frames, susie_target_size)
    # Ralsei
    ralsei_intro_frames = scale_all_to_target(ralsei_intro_frames, ralsei_target_size)
    ralsei_idle_frames = scale_all_to_target(ralsei_idle_frames, ralsei_target_size)
    # Knight (4x idle size)
    knight_idle_orig_size = (knight_idle_img.get_width(), knight_idle_img.get_height())
    knight_target_size = (int(knight_idle_orig_size[0] * 3), int(knight_idle_orig_size[1] * 3))
    knight_intro_frames = scale_all_to_target(knight_intro_frames, knight_target_size)
    knight_idle_img = pygame.transform.smoothscale(knight_idle_img, knight_target_size)

    # After scaling to target size, manually scale up intro frames to visually match idle sprites
    kris_intro_frames = [pygame.transform.smoothscale(f, (int(f.get_width() * 1.5), int(f.get_height() * 1.5))) for f in kris_intro_frames]
    susie_intro_frames = [pygame.transform.smoothscale(f, (int(f.get_width() * 1.5), int(f.get_height() * 1.5))) for f in susie_intro_frames]

    # Animation lengths
    knight_len = len(knight_intro_frames)
    kris_len = len(kris_intro_frames)
    susie_len = len(susie_intro_frames)
    ralsei_len = len(ralsei_intro_frames)

    knight_pause_frame = 7  # pause after frame 6 (index 6), on frame 7
    knight_pause_duration = 6  # frames to pause (shorter pause)
    knight_total_frames = knight_len + knight_pause_duration

    # Other intros start at the pause
    kris_start = knight_pause_frame
    susie_start = knight_pause_frame
    ralsei_start = knight_pause_frame
    max_frames = max(knight_total_frames, kris_start + kris_len, susie_start + susie_len, ralsei_start + ralsei_len)

    # Calculate Roaring Knight position (3x size, 100px to right of battle box)
    knight_rect = knight_idle_img.get_rect()
    knight_rect.centery = kris_rect.centery
    knight_rect.left = battle_box_rect.right + 40
    knight_idle_base_y = knight_rect.top

    clock = pygame.time.Clock()
    # Prepare sound effect for knight intro
    battle_start_sfx = pygame.mixer.Sound(os.path.join(base_dir, 'sprites', 'sound_effects', 'battle_start.wav'))
    battle_start_sfx_played = False
    for i in range(max_frames):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        screen.blit(bg_img, (0, 0))
        # Draw fountain
        fountain_img = fountain_scaled_frames[fountain_frame_idx]
        fountain_rect = fountain_img.get_rect()
        fountain_rect.left = kris_rect.left + kris_rect.width + 100
        fountain_rect.top = 0
        screen.blit(fountain_img, fountain_rect)
        # Kris
        if i >= kris_start and (i - kris_start) < kris_len:
            intro_img = kris_intro_frames[i - kris_start]
            intro_rect = intro_img.get_rect()
            intro_rect.center = kris_rect.center  # align centers
            screen.blit(intro_img, intro_rect)
        else:
            screen.blit(kris_idle_frames[0], kris_rect)
        # Susie
        if i >= susie_start and (i - susie_start) < susie_len:
            intro_img = susie_intro_frames[i - susie_start]
            intro_rect = intro_img.get_rect()
            intro_rect.center = susie_rect.center  # align centers
            screen.blit(intro_img, intro_rect)
        else:
            screen.blit(susie_idle_frames[0], susie_rect)
        # Ralsei
        if i >= ralsei_start and (i - ralsei_start) < ralsei_len:
            screen.blit(ralsei_intro_frames[i - ralsei_start], ralsei_rect)
        else:
            screen.blit(ralsei_idle_frames[0], ralsei_rect)
        # Roaring Knight
        if i < knight_pause_frame:
            screen.blit(knight_intro_frames[i], knight_rect)
        elif i < knight_pause_frame + knight_pause_duration:
            screen.blit(knight_intro_frames[knight_pause_frame], knight_rect)
            # Play sound at the second to last frame (index knight_pause_frame-2)
            if i == 12 and not battle_start_sfx_played:
                battle_start_sfx.play()
                battle_start_sfx_played = True
        elif (i - knight_pause_duration) < knight_len:
            screen.blit(knight_intro_frames[i - knight_pause_duration], knight_rect)
        else:
            # Idle, float up and down
            float_offset = int(20 * math.sin(pygame.time.get_ticks() / 267))
            idle_rect = knight_rect.copy()
            idle_rect.top = knight_idle_base_y + float_offset
            screen.blit(knight_idle_img, idle_rect)
        pygame.display.flip()
        clock.tick(16)  # 16 FPS for cutscene

    # Draw the main scene after the intro
    draw_main_scene(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, False
    )
    pygame.display.flip()

    # Idle animation loop before Attack1
    idle_duration = 500  # milliseconds (3 seconds)
    idle_start = pygame.time.get_ticks()
    player_speed = 5  # Ensure player_speed is defined here
    while pygame.time.get_ticks() - idle_start < idle_duration:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                sys.exit()
        # Handle player movement (copied from main loop)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            player_x -= player_speed
        if keys[pygame.K_RIGHT]:
            player_x += player_speed
        if keys[pygame.K_UP]:
            player_y -= player_speed
        if keys[pygame.K_DOWN]:
            player_y += player_speed
        # Clamp player position to inside the battle box
        playable_rect = battle_box_rect.inflate(-2 * battle_box_border, -2 * battle_box_border)
        player_x = max(playable_rect.left, min(player_x, playable_rect.right - heart_size))
        player_y = max(playable_rect.top, min(player_y, playable_rect.bottom - heart_size))
        # Advance animation frames
        fountain_anim_timer += 1
        if fountain_anim_timer >= fountain_anim_speed:
            fountain_frame_idx = (fountain_frame_idx + 1) % fountain_frame_count
            fountain_anim_timer = 0
        kris_anim_timer += 1
        if kris_anim_timer >= kris_anim_speed:
            kris_frame_idx = (kris_frame_idx + 1) % kris_frame_count
            kris_anim_timer = 0
        susie_anim_timer += 1
        if susie_anim_timer >= susie_anim_speed:
            susie_frame_idx = (susie_frame_idx + 1) % susie_frame_count
            susie_anim_timer = 0
        ralsei_anim_timer += 1
        if ralsei_anim_timer >= ralsei_anim_speed:
            ralsei_frame_idx = (ralsei_frame_idx + 1) % ralsei_frame_count
            ralsei_anim_timer = 0
        draw_main_scene(
            screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
            kris_idle_frames, kris_frame_idx, kris_rect,
            susie_idle_frames, susie_frame_idx, susie_rect,
            ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
            battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, False,
            knight_idle_img, True, clock
        )
        pygame.display.flip()
        clock.tick(60)


    # Draw the main scene after the first attack to clear leftovers
    draw_main_scene(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, False,
        knight_idle_img, True, clock
    )
    pygame.display.flip()
    return player_x, player_y

def PreAttack1(
    screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
    kris_rect, battle_box_rect, knight_idle_img, clock,
    battle_box_color, battle_box_border_color, battle_box_border,
    heart_img_0, heart_img_1, player_x, player_y, heart_size,
    kris_idle_frames, kris_frame_idx, kris_rect_in, susie_idle_frames, susie_frame_idx, susie_rect_in,
    ralsei_idle_frames, ralsei_frame_idx, ralsei_rect_in,
    player_speed=5
):
    global knight_trail, trail_length, trail_alphas
    # Input lockout for 200ms to prevent accidental movement from held keys
        # Animation frame/timer setup for animating fountain, Kris, Susie, Ralsei
    # Use the passed-in frame indices and timers to maintain sync with main function
    local_fountain_frame_idx = fountain_frame_idx
    local_kris_frame_idx = kris_frame_idx
    local_susie_frame_idx = susie_frame_idx
    local_ralsei_frame_idx = ralsei_frame_idx
    local_fountain_anim_timer = pygame.time.get_ticks()
    local_kris_anim_timer = 0
    local_susie_anim_timer = 0
    local_ralsei_anim_timer = 0

    input_lockout_duration = 200  # ms
    attack1_start_time = pygame.time.get_ticks()
    movement_keys_released = False
    # Load Knight point animation frames
    knight_point_dir = os.path.join(os.path.dirname(__file__), 'sprites', 'spr_roaringknight_point_ol')
    knight_point_files = sorted([
        os.path.join(knight_point_dir, f) for f in os.listdir(knight_point_dir)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ])
    knight_point_frames = [pygame.image.load(f).convert_alpha() for f in knight_point_files]
    # Scale to match idle size
    knight_point_frames = [pygame.transform.smoothscale(f, knight_idle_img.get_size()) for f in knight_point_frames]

    # Start and end positions
    start_x = battle_box_rect.right + 40
    start_y = kris_rect.centery + 20
    end_x = battle_box_rect.right + 10  # closer to the box
    end_y = battle_box_rect.centery
    move_duration = 1000  # ms
    anim_duration = 1000  # ms for 5 frames
    start_time = pygame.time.get_ticks()
    running = True
    while running:
        now = pygame.time.get_ticks()
        t = min((now - start_time) / move_duration, 1.0)
        # Interpolate position
        knight_x = int(start_x + (end_x - start_x) * t)
        knight_y = int(start_y + (end_y - start_y) * t)
        # Animation frame
        frame_idx = min(int((now - start_time) / (anim_duration / len(knight_point_frames))), len(knight_point_frames) - 1)
        knight_img = knight_point_frames[frame_idx]
        knight_rect = knight_img.get_rect()
        knight_rect.left = knight_x
        knight_rect.centery = knight_y
        # Only allow player movement after input lockout and after all movement keys are released
        keys = pygame.key.get_pressed()
        movement_keys = [keys[pygame.K_LEFT], keys[pygame.K_RIGHT], keys[pygame.K_UP], keys[pygame.K_DOWN]]
        if now - attack1_start_time > input_lockout_duration:
            if not movement_keys_released:
                if not any(movement_keys):
                    movement_keys_released = True
            else:
                if keys[pygame.K_LEFT]:
                    player_x -= player_speed
                if keys[pygame.K_RIGHT]:
                    player_x += player_speed
                if keys[pygame.K_UP]:
                    player_y -= player_speed
                if keys[pygame.K_DOWN]:
                    player_y += player_speed
        # Clamp player position to inside the battle box
        playable_rect = battle_box_rect.inflate(-2 * battle_box_border, -2 * battle_box_border)
        player_x = max(playable_rect.left, min(player_x, playable_rect.right - heart_size))
        player_y = max(playable_rect.top, min(player_y, playable_rect.bottom - heart_size))
        # Trail logic
        knight_trail.insert(0, (knight_img.copy(), knight_rect.copy()))
        if len(knight_trail) > trail_length:
            knight_trail.pop()
        # --- Animate all idle/backgrounds ---
        
        local_kris_anim_timer += 1
        if local_kris_anim_timer >= 8:
            local_kris_frame_idx = (local_kris_frame_idx + 1) % len(kris_idle_frames)
            local_kris_anim_timer = 0
        local_susie_anim_timer += 1
        if local_susie_anim_timer >= 8:
            local_susie_frame_idx = (local_susie_frame_idx + 1) % len(susie_idle_frames)
            local_susie_anim_timer = 0
        local_ralsei_anim_timer += 1
        if local_ralsei_anim_timer >= 8:
            local_ralsei_frame_idx = (local_ralsei_frame_idx + 1) % len(ralsei_idle_frames)
            local_ralsei_anim_timer = 0
        # Advance animation frames
        if now - local_fountain_anim_timer > 100:  # change frame every 100ms
            local_fountain_frame_idx = (local_fountain_frame_idx + 1) % 4
            local_fountain_anim_timer = now
       

        # Recalculate character rects for current frames (match draw_main_scene logic)
        kris_img = kris_idle_frames[local_kris_frame_idx]
        kris_rect_dyn = kris_img.get_rect()
        kris_rect_dyn.left = kris_rect_in.left
        kris_rect_dyn.centery = kris_rect_in.centery

        susie_img = susie_idle_frames[local_susie_frame_idx]
        susie_rect_dyn = susie_img.get_rect()
        susie_rect_dyn.left = kris_rect_dyn.left - 120
        susie_rect_dyn.centery = kris_rect_dyn.centery + 100

        ralsei_img = ralsei_idle_frames[local_ralsei_frame_idx]
        ralsei_rect_dyn = ralsei_img.get_rect()
        ralsei_rect_dyn.left = susie_rect_dyn.left - 10
        ralsei_rect_dyn.centery = susie_rect_dyn.centery + 100
        
        screen.blit(fountain_scaled_frames[0], (100, 100))

        # Draw everything using draw_main_scene
        draw_main_scene(
            screen, bg_img, fountain_scaled_frames, local_fountain_frame_idx,
            kris_idle_frames, local_kris_frame_idx, kris_rect_dyn,
            susie_idle_frames, local_susie_frame_idx, susie_rect_dyn,
            ralsei_idle_frames, local_ralsei_frame_idx, ralsei_rect_dyn,
            battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, None, 0, False,
            None, False, clock
        )
        # Draw trail and knight on top
        for i, (img, rect) in enumerate(reversed(knight_trail)):
            img = img.copy()
            img.set_alpha(trail_alphas[i])
            rect = rect.copy()
            rect.left += 40 + i * 10
            screen.blit(img, rect)
        screen.blit(knight_img, knight_rect)
        pygame.display.flip()
        clock.tick(60)
        # End condition: when movement and animation are done
        if t >= 1.0 and frame_idx == len(knight_point_frames) - 1:
            running = False

    # Hold the final pose for 0.5 seconds (500 ms)
    hold_time = 500  # ms
    hold_start = pygame.time.get_ticks()
    while pygame.time.get_ticks() - hold_start < hold_time:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        # Handle player movement
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            player_x -= player_speed
        if keys[pygame.K_RIGHT]:
            player_x += player_speed
        if keys[pygame.K_UP]:
            player_y -= player_speed
        if keys[pygame.K_DOWN]:
            player_y += player_speed
        # Clamp player position to inside the battle box
        playable_rect = battle_box_rect.inflate(-2 * battle_box_border, -2 * battle_box_border)
        player_x = max(playable_rect.left, min(player_x, playable_rect.right - heart_size))
        player_y = max(playable_rect.top, min(player_y, playable_rect.bottom - heart_size))
        # Redraw the final frame and trail
        bg_img_scaled = pygame.transform.scale(bg_img, (screen.get_width(), screen.get_height()))
        screen.blit(bg_img_scaled, (0, 0))
        pygame.draw.rect(screen, battle_box_color, battle_box_rect)
        pygame.draw.rect(screen, battle_box_border_color, battle_box_rect, battle_box_border)
        screen.blit(heart_img_0, (player_x, player_y))
        fountain_img = fountain_scaled_frames[local_fountain_frame_idx]
        fountain_rect = fountain_img.get_rect()
        fountain_rect.left = kris_rect_in.left + kris_rect_in.width + 100
        fountain_rect.top = 0
        screen.blit(fountain_img, fountain_rect) # I didn't have this line before
        screen.blit(kris_idle_frames[local_kris_frame_idx], kris_rect_in)
        screen.blit(susie_idle_frames[local_susie_frame_idx], susie_rect_in)
        screen.blit(ralsei_idle_frames[local_ralsei_frame_idx], ralsei_rect_in)
        for i, (img, rect) in enumerate(reversed(knight_trail)):
            img = img.copy()
            img.set_alpha(trail_alphas[i])
            rect = rect.copy()
            rect.left += 40 + i * 10
            screen.blit(img, rect)
        screen.blit(knight_point_frames[-1], knight_rect)
        pygame.display.flip()
        clock.tick(60)

    # Define variables for return
    triangle_knight_img = knight_point_frames[-1]
    triangle_knight_rect = knight_rect
    triangle_start_time = pygame.time.get_ticks()
    knight_reverse_duration = 500  # ms, adjust as needed

    return knight_point_frames[-1], knight_rect, knight_point_frames, player_x, player_y, \
    triangle_knight_img, triangle_knight_rect, triangle_start_time, knight_reverse_duration, knight_idle_img, \
    local_fountain_frame_idx, local_kris_frame_idx, local_susie_frame_idx, local_ralsei_frame_idx, \
    local_fountain_anim_timer, local_kris_anim_timer, local_susie_anim_timer, local_ralsei_anim_timer


# Move the triangle, star, and starchild attack logic from main() into a new class called Attack1
class Attack1:
    def __init__(self, screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
    kris_idle_frames, kris_frame_idx, kris_rect,
    susie_idle_frames, susie_frame_idx, susie_rect,
    ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
    battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
    heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives,
    knight_point_img, knight_point_rect, knight_point_frames,
    clock, player_speed,
    screen_height, base_dir, knight_point_trail,
    fountain_anim_speed, fountain_frame_count,
    kris_anim_speed, kris_frame_count,
    susie_anim_speed, susie_frame_count,
    ralsei_anim_speed, ralsei_frame_count,
    fountain_anim_timer, kris_anim_timer, susie_anim_timer, ralsei_anim_timer,
    invincible_until, triangle_start_time, triangle_knight_img, triangle_knight_rect, 
    knight_reverse_duration, knight_idle_img,starchild_scale=1.0):
        self.screen = screen
        self.bg_img = bg_img
        self.fountain_scaled_frames = fountain_scaled_frames
        self.fountain_frame_idx = fountain_frame_idx
        self.kris_idle_frames = kris_idle_frames
        self.kris_frame_idx = kris_frame_idx
        self.kris_rect = kris_rect
        self.susie_idle_frames = susie_idle_frames
        self.susie_frame_idx = susie_frame_idx
        self.susie_rect = susie_rect
        self.ralsei_idle_frames = ralsei_idle_frames
        self.ralsei_frame_idx = ralsei_frame_idx
        self.ralsei_rect = ralsei_rect
        self.battle_box_rect = battle_box_rect
        self.battle_box_color = battle_box_color
        self.battle_box_border_color = battle_box_border_color
        self.battle_box_border = battle_box_border
        self.heart_img_0 = heart_img_0
        self.heart_img_1 = heart_img_1
        self.player_x = player_x
        self.player_y = player_y
        self.heart_size = heart_size
        self.font = font
        self.player_lives = player_lives
        self.knight_point_img = knight_point_img
        self.knight_point_rect = knight_point_rect
        self.knight_point_frames = knight_point_frames
        self.clock = clock
        self.player_speed = player_speed
        self.screen_height = screen_height
        self.base_dir = base_dir
        self.knight_point_trail = knight_point_trail
        self.fountain_anim_speed = fountain_anim_speed
        self.fountain_frame_count = fountain_frame_count
        self.kris_anim_speed = kris_anim_speed
        self.kris_frame_count = kris_frame_count
        self.susie_anim_speed = susie_anim_speed
        self.susie_frame_count = susie_frame_count
        self.ralsei_anim_speed = ralsei_anim_speed
        self.ralsei_frame_count = ralsei_frame_count
        self.fountain_anim_timer = fountain_anim_timer
        self.kris_anim_timer = kris_anim_timer
        self.susie_anim_timer = susie_anim_timer
        self.ralsei_anim_timer = ralsei_anim_timer
        self.invincible_until = invincible_until
        self.triangle_start_time = triangle_start_time
        self.triangle_knight_img = triangle_knight_img
        self.triangle_knight_rect = triangle_knight_rect
        self.knight_reverse_duration = knight_reverse_duration
        self.knight_idle_img = knight_idle_img
        self.starchild_scale = starchild_scale
        
        # Initialize attack state
        self.attack_phase = 'triangle'
        self.triangle_active = True
        self.triangle_start_time = pygame.time.get_ticks()
        self.triangle_knight_img = self.knight_point_img.copy()
        self.triangle_knight_rect = self.knight_point_rect.copy()
        self.knight_point_trail.clear()
        self.knight_point_trail.append((self.triangle_knight_img.copy(), self.triangle_knight_rect.copy()))
        self.knight_reverse_anim = False
        self.knight_reverse_start = 0
        self.knight_reverse_idx = 0
        self.knight_reverse_frames = []
        self.knight_idle_timer = 0
        self.knight_idle_allowed = False
        self.idle_redraw_once = False
        
        # Load assets
        self.load_assets()
        
    def load_assets(self):
        # Triangle effect setup
        triangle_tip = (self.triangle_knight_rect.left, self.triangle_knight_rect.centery)
        triangle_bottom = (0, self.screen_height)
        triangle_top = (0, -50)
        triangle_points = [triangle_tip, triangle_bottom, triangle_top]
        xs = [p[0] for p in triangle_points]
        ys = [p[1] for p in triangle_points]
        triangle_min_x, triangle_max_x = min(xs), max(xs)
        triangle_min_y, triangle_max_y = min(ys), max(ys)
        triangle_width = triangle_max_x - triangle_min_x
        triangle_height = triangle_max_y - triangle_min_y
        
        # Create fill surface
        flow0 = pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_purple_star_flow', 'spr_knight_bullet_flow_0.png')).convert_alpha()
        flow0.set_alpha(150)
        stretched_img = pygame.transform.smoothscale(flow0, (triangle_width, triangle_height))
        fill_surf = pygame.Surface((triangle_width, triangle_height), pygame.SRCALPHA)
        fill_surf.blit(stretched_img, (0, 0))
        mask_surf = pygame.Surface((triangle_width, triangle_height), pygame.SRCALPHA)
        tri_points = [(x - triangle_min_x, y - triangle_min_y) for (x, y) in triangle_points]
        pygame.draw.polygon(mask_surf, (255, 255, 255, 255), tri_points)
        fill_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self.triangle_fill_surf = fill_surf
        
        # Play sound
        sfx_path = os.path.join(self.base_dir, 'sprites', 'sound_effects', 'purple_blast.wav')
        self.sfx = pygame.mixer.Sound(sfx_path)
        self.sfx.set_volume(1.0)
        self.sfx.play(fade_ms=0)

        # For moving bullet and sliding battle box
        bullet1_img_orig = pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_purple_star_flow', 'spr_knight_bullet_flow_1.png')).convert_alpha()
        bullet1_scale = 2.5
        self.bullet1_img = pygame.transform.smoothscale(
            bullet1_img_orig,
            (int(bullet1_img_orig.get_width() * bullet1_scale), int(bullet1_img_orig.get_height() * bullet1_scale))
        )
        self.bullet1_img.set_alpha(180)
        self.battle_box_slide_px = 90
        self.battle_box_slide_duration = 3000
        self.battle_box_slide_start = self.battle_box_rect.left

        # For star bullets
        star_bullet_img = pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_bullet_star', 'spr_knight_bullet_star_0.png')).convert_alpha()
        star_bullet_img = pygame.transform.smoothscale(star_bullet_img, (int(star_bullet_img.get_width() * 1.5), int(star_bullet_img.get_height() * 1.5)))
        self.star_bullets = []
        self.star_bullets_spawned = False
        self.star_bullet_base_speed = 700
        self.star_bullet_duration = 3000
        self.num_star_bullets = 20
        self.star_attack_sfx = pygame.mixer.Sound(os.path.join(self.base_dir, 'sprites', 'sound_effects', 'star_attack.wav'))

        # Add a phase for star bullet reversal
        self.star_reverse_duration = 1000
        self.star_reverse_start = 0

        # Load star bullet animation frames
        self.star_bullet_img_0 = star_bullet_img
        self.star_bullet_img_1 = pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_bullet_star', 'spr_knight_bullet_star_1.png')).convert_alpha()
        self.star_bullet_img_1 = pygame.transform.smoothscale(self.star_bullet_img_1, (int(self.star_bullet_img_1.get_width() * 1.5), int(self.star_bullet_img_1.get_height() * 1.5)))
        self.star_bullet_img_2 = pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_bullet_star', 'spr_knight_bullet_star_2.png')).convert_alpha()
        self.star_bullet_img_2 = pygame.transform.smoothscale(self.star_bullet_img_2, (int(self.star_bullet_img_2.get_width() * 1.5), int(self.star_bullet_img_2.get_height() * 1.5)))
        self.star_bullet_img_3 = pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_bullet_star', 'spr_knight_bullet_star_3.png')).convert_alpha()
        self.star_bullet_img_3 = pygame.transform.smoothscale(self.star_bullet_img_3, (int(self.star_bullet_img_3.get_width() * 2), int(self.star_bullet_img_3.get_height() * 2)))
        
        # Load starchild projectiles (up and down) with scale
        starchild_img_up = pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_starchild', 'spr_knight_starchild_up.png')).convert_alpha()
        starchild_img_up = pygame.transform.smoothscale(starchild_img_up, (int(starchild_img_up.get_width() * 1.2 * self.starchild_scale), int(starchild_img_up.get_height() * 1.2 * self.starchild_scale)))
        starchild_img_down = pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_starchild', 'spr_knight_starchild_down.png')).convert_alpha()
        starchild_img_down = pygame.transform.smoothscale(starchild_img_down, (int(starchild_img_down.get_width() * 1.2 * self.starchild_scale), int(starchild_img_down.get_height() * 1.2 * self.starchild_scale)))
        self.starchild_img_up = starchild_img_up
        self.starchild_img_down = starchild_img_down
        self.starchilds = []
        self.starchilds_spawned = False
        self.starchild_speed = 160
        self.starchild_delay_early = 0
        self.starchild_delay_late = 120

        # Add a flag to trigger starchild explosion only after star_reverse phase is fully complete
        self.starchilds_pending_explosion = False
        self.starchilds_exploded = False
        self.starchilds_display_start = None
        
        self.screen_rect = self.screen.get_rect()

    def run(self):
        global knight_trail, trail_length, trail_alphas
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False

            # Draw background
            bg_img_scaled = pygame.transform.scale(self.bg_img, (self.screen.get_width(), self.screen.get_height()))
            self.screen.blit(bg_img_scaled, (0, 0))

            # Draw Kris's idle animation (define kris_rect first)
            kris_img = self.kris_idle_frames[self.kris_frame_idx]
            kris_rect = kris_img.get_rect()
            kris_rect.left = 350  # 350px from left
            kris_rect.centery = self.screen_height // 2 - 100  
            self.screen.blit(kris_img, kris_rect)

            # Draw fountain animation (cycling 4 frames), now kris_rect is defined
            fountain_img = self.fountain_scaled_frames[self.fountain_frame_idx]
            fountain_rect = fountain_img.get_rect()
            fountain_rect.left = kris_rect.left + kris_rect.width + 100  # 100px to the right of Kris
            fountain_rect.top = 0  # top of the screen
            # Adjust height so bottom is 100px above Kris
            desired_bottom = kris_rect.centery - kris_rect.height // 2 - 100
            if fountain_rect.height > desired_bottom:
                # Crop the bottom if needed
                crop_height = desired_bottom
                cropped_img = pygame.Surface((fountain_rect.width, crop_height), pygame.SRCALPHA)
                cropped_img.blit(fountain_img, (0, 0), (0, 0, fountain_rect.width, crop_height))
                fountain_img = cropped_img
                fountain_rect = fountain_img.get_rect()
                fountain_rect.left = kris_rect.left + kris_rect.width + 100
                fountain_rect.top = 0
            self.screen.blit(fountain_img, fountain_rect)

            # Draw Susie's idle animation
            susie_img = self.susie_idle_frames[self.susie_frame_idx]
            susie_rect = susie_img.get_rect()
            susie_rect.left = kris_rect.left - 120
            susie_rect.centery = kris_rect.centery + 100  # 100px below Kris
            self.screen.blit(susie_img, susie_rect)

            # Draw Ralsei's idle animation
            ralsei_img = self.ralsei_idle_frames[self.ralsei_frame_idx]
            ralsei_rect = ralsei_img.get_rect()
            ralsei_rect.left = susie_rect.left - 10  # 30px to the left of Susie
            ralsei_rect.centery = susie_rect.centery + 100  # 100px below Susie
            self.screen.blit(ralsei_img, ralsei_rect)

            # Draw battle box (black square with green border)
            pygame.draw.rect(self.screen, self.battle_box_color, self.battle_box_rect)
            pygame.draw.rect(self.screen, self.battle_box_border_color, self.battle_box_rect, self.battle_box_border)

            # Handle player movement
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                self.player_x -= self.player_speed
            if keys[pygame.K_RIGHT]:
                self.player_x += self.player_speed
            if keys[pygame.K_UP]:
                self.player_y -= self.player_speed
            if keys[pygame.K_DOWN]:
                self.player_y += self.player_speed
            # Clamp player position to inside the battle box
            playable_rect = self.battle_box_rect.inflate(-2 * self.battle_box_border, -2 * self.battle_box_border)
            self.player_x = max(playable_rect.left, min(self.player_x, playable_rect.right - self.heart_size))
            self.player_y = max(playable_rect.top, min(self.player_y, playable_rect.bottom - self.heart_size))

            # Collision detection for star bullets and starchilds
            player_rect = pygame.Rect(self.player_x, self.player_y, self.heart_size, self.heart_size)
            player_center = (self.player_x + self.heart_size // 2, self.player_y + self.heart_size // 2)
            hit_this_frame = False
            # Star bullets (during triangle, reverse, star_reverse)
            if self.attack_phase in ('triangle', 'reverse', 'star_reverse'):
                for bullet in self.star_bullets:
                    if bullet.get('x') is not None and bullet.get('y') is not None:
                        r = self.star_bullet_img_0.get_width() // 3
                        dx = bullet['x'] - player_center[0]
                        dy = bullet['y'] - player_center[1]
                        if dx * dx + dy * dy < r * r:
                            hit_this_frame = True
                            break
            # Starchilds (after explosion)
            for sc in self.starchilds:
                if pygame.time.get_ticks() >= sc['spawn_time']:
                    sc['x'] += sc['vx'] / 60.0
                    sc['y'] += sc['vy'] / 60.0
                    # Select the correct image and rotation
                    if sc['img'] == 'up':
                        base_img = self.starchild_img_up
                    else:
                        base_img = self.starchild_img_down
                    rotated_img = pygame.transform.rotate(base_img, sc['angle'])
                    rect = rotated_img.get_rect(center=(int(sc['x']), int(sc['y'])))
                    if self.screen_rect.colliderect(rect):
                        self.screen.blit(rotated_img, rect)
                    # Use full rect for hitbox
                    if rect.collidepoint(player_center):
                        hit_this_frame = True
                        break
            # Invincibility logic
            if pygame.time.get_ticks() < self.invincible_until:
                invincible = True
            else:
                invincible = False
            if hit_this_frame and not invincible:
                self.player_lives = max(0, self.player_lives - 1)
                self.invincible_until = pygame.time.get_ticks() + 1000  # 1 second invincibility
                invincible = True

            # Draw lives counter
            lives_surf = self.font.render(f"LIVES: {self.player_lives}", True, (255, 255, 255))
            self.screen.blit(lives_surf, (50, 50))

            # Draw player heart (flashing if invincible)
            if invincible:
                # Alternate every 100ms
                if ((pygame.time.get_ticks() // 100) % 2) == 0:
                    heart_draw_img = self.heart_img_0
                else:
                    heart_draw_img = self.heart_img_1
            else:
                heart_draw_img = self.heart_img_0
            self.screen.blit(heart_draw_img, (self.player_x, self.player_y))

            # Draw the Knight and its trail depending on attack_phase
            if self.attack_phase == 'triangle':
                now = pygame.time.get_ticks()
                elapsed = now - self.triangle_start_time
                # Slide the battle box left over 3 seconds
                slide_offset = int(self.battle_box_slide_px * min(elapsed / self.battle_box_slide_duration, 1.0))
                self.battle_box_rect.left = self.battle_box_slide_start - slide_offset
                # Redraw the triangle points and fill to match the new box position
                # Do NOT move the Knight with the battle box
                # triangle_knight_rect.left and centery remain fixed
                triangle_tip = (self.triangle_knight_rect.left, self.triangle_knight_rect.centery)
                triangle_bottom = (0, self.screen_height)
                triangle_top = (0, -50)
                triangle_points = [triangle_tip, triangle_bottom, triangle_top]
                xs = [p[0] for p in triangle_points]
                ys = [p[1] for p in triangle_points]
                triangle_min_x, triangle_max_x = min(xs), max(xs)
                triangle_min_y, triangle_max_y = min(ys), max(ys)
                triangle_width = triangle_max_x - triangle_min_x
                triangle_height = triangle_max_y - triangle_min_y
                # Recreate fill surface for the triangle
                flow0 = pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_purple_star_flow', 'spr_knight_bullet_flow_0.png')).convert_alpha()
                flow0.set_alpha(150)
                stretched_img = pygame.transform.smoothscale(flow0, (triangle_width, triangle_height))
                fill_surf = pygame.Surface((triangle_width, triangle_height), pygame.SRCALPHA)
                fill_surf.blit(stretched_img, (0, 0))
                mask_surf = pygame.Surface((triangle_width, triangle_height), pygame.SRCALPHA)
                tri_points = [(x - triangle_min_x, y - triangle_min_y) for (x, y) in triangle_points]
                pygame.draw.polygon(mask_surf, (255, 255, 255, 255), tri_points)
                fill_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                self.triangle_fill_surf = fill_surf
                # Draw the filled triangle
                self.screen.blit(self.triangle_fill_surf, (triangle_min_x, triangle_min_y))
                # Animate bullet1 starting 10px to the left of the Knight's tip and moving left at 2x speed
                bullet1_start_x = triangle_tip[0] - self.bullet1_img.get_width() // 2 - 10
                bullet1_end_x = -self.bullet1_img.get_width()  # Move out of bounds to the left
                bullet1_progress = min(elapsed / 1500, 1.0)  # 1.5 seconds for 2x speed
                bullet1_x = int(bullet1_start_x + (bullet1_end_x - bullet1_start_x) * bullet1_progress)
                # Place bullet lower, closer to the vertical center of the triangle (e.g., 0.55 from tip to bottom)
                bullet1_y = int(triangle_tip[1] + (triangle_bottom[1] - triangle_tip[1]) * 0.55)
                self.screen.blit(self.bullet1_img, (bullet1_x, bullet1_y - self.bullet1_img.get_height() // 2))

                # Spawn star bullets with random delays and play sound for each
                if not self.star_bullets_spawned:
                    self.star_bullets.clear()
                    spawn_times = sorted([random.uniform(0, 3000) for _ in range(self.num_star_bullets)])
                    for st in spawn_times:
                        target_x = -50
                        target_y = random.uniform(-100, self.screen_height + 100)
                        dx = target_x - triangle_tip[0]
                        dy = target_y - triangle_tip[1]
                        speed_factor = random.uniform(1, 1.75)
                        duration = self.star_bullet_duration / 1000.0 / speed_factor
                        vx = dx / duration
                        vy = dy / duration
                        self.star_bullets.append({'x': triangle_tip[0], 'y': triangle_tip[1], 'vx': vx, 'vy': vy, 'spawn_time': st, 'active': False})
                    self.star_bullets_spawned = True
                    star_bullet_start_time = now
                # Update and draw star bullets
                for bullet in self.star_bullets:
                    t = now - star_bullet_start_time
                    if not bullet['active'] and t >= bullet['spawn_time']:
                        bullet['active'] = True
                        # Play sound for each star spawn
                        self.star_attack_sfx.play()
                        bullet['start_x'] = triangle_tip[0]
                        bullet['start_y'] = triangle_tip[1]
                    if bullet['active']:
                        dt = t - bullet['spawn_time']
                        if dt < self.star_bullet_duration:
                            bullet['x'] = bullet['start_x'] + bullet['vx'] * (dt / 1000.0)
                            bullet['y'] = bullet['start_y'] + bullet['vy'] * (dt / 1000.0)
                            # Only draw the default star bullet sprite during the forward phase
                            self.screen.blit(self.star_bullet_img_0, (int(bullet['x'] - self.star_bullet_img_0.get_width() // 2), int(bullet['y'] - self.star_bullet_img_0.get_height() // 2)))
                # Update and draw the trail for the pointing Knight
                self.knight_point_trail.insert(0, (self.triangle_knight_img.copy(), self.triangle_knight_rect.copy()))
                if len(self.knight_point_trail) > trail_length:
                    self.knight_point_trail.pop()
                for i, (img, rect) in enumerate(reversed(self.knight_point_trail)):
                    img = img.copy()
                    img.set_alpha(trail_alphas[i])
                    rect = rect.copy()
                    rect.left += 40 + i * 10
                    self.screen.blit(img, rect)
                # Draw the Knight sprite (pointing frame)
                self.screen.blit(self.triangle_knight_img, self.triangle_knight_rect)
                if elapsed > 3000:  # 3 seconds for triangle phase
                    self.attack_phase = 'reverse'
                    self.knight_reverse_start = pygame.time.get_ticks()
                    self.knight_reverse_frames = list(reversed(self.knight_point_frames))
                    self.knight_reverse_idx = 0
                    # Prepare for star reversal
                    for bullet in self.star_bullets:
                        bullet['orig_vx'] = bullet['vx']
                        bullet['orig_vy'] = bullet['vy']
                        bullet['reverse_x'] = bullet['x']
                        bullet['reverse_y'] = bullet['y']
                    self.star_reverse_start = 0
            elif self.attack_phase == 'reverse':
                now = pygame.time.get_ticks()
                reverse_elapsed = now - self.knight_reverse_start
                frame_time = self.knight_reverse_duration / max(1, len(self.knight_reverse_frames))
                self.knight_reverse_idx = min(int(reverse_elapsed // frame_time), len(self.knight_reverse_frames) - 1)
                knight_img = self.knight_reverse_frames[self.knight_reverse_idx]
                knight_rect = knight_img.get_rect()
                knight_rect.left = self.triangle_knight_rect.left
                knight_rect.centery = self.triangle_knight_rect.centery
                # Update and draw the trail for the reverse animation
                self.knight_point_trail.insert(0, (knight_img.copy(), knight_rect.copy()))
                if len(self.knight_point_trail) > trail_length:
                    self.knight_point_trail.pop()
                for i, (img, rect) in enumerate(reversed(self.knight_point_trail)):
                    img = img.copy()
                    img.set_alpha(trail_alphas[i])
                    rect = rect.copy()
                    rect.left += 40 + i * 10
                    self.screen.blit(img, rect)
                self.screen.blit(knight_img, knight_rect)
                # Draw the star bullets at their last position from the triangle phase
                for bullet in self.star_bullets:
                    if bullet.get('x') is not None and bullet.get('y') is not None:
                        # Only draw the default star bullet sprite during the reverse phase
                        self.screen.blit(self.star_bullet_img_0, (int(bullet['x'] - self.star_bullet_img_0.get_width() // 2), int(bullet['y'] - self.star_bullet_img_0.get_height() // 2)))
                if self.knight_reverse_idx == len(self.knight_reverse_frames) - 1:
                    self.attack_phase = 'star_reverse'
                    self.star_reverse_start = pygame.time.get_ticks()
                    for bullet in self.star_bullets:
                        bullet['vx'] = -bullet['orig_vx']
                        bullet['vy'] = -bullet['orig_vy']
                        bullet['x'] = bullet['reverse_x']
                        bullet['y'] = bullet['reverse_y']
                        bullet['spawn_time'] = self.star_reverse_start
                    self.knight_idle_timer = pygame.time.get_ticks()
            elif self.attack_phase == 'star_reverse':
                now = pygame.time.get_ticks()
                reverse_elapsed = now - self.star_reverse_start
                for bullet in self.star_bullets:
                    if bullet.get('vx') is not None:
                        # Use reverse_elapsed for all bullets in this phase
                        dt = min(reverse_elapsed, self.star_reverse_duration)
                        bullet['x'] = bullet['reverse_x'] + bullet['vx'] * (dt / 1000.0)
                        bullet['y'] = bullet['reverse_y'] + bullet['vy'] * (dt / 1000.0)
                        # Animate star bullet: 0 -> 1 -> 2 only during the backward phase
                        star_anim_img = self.star_bullet_img_0
                        if dt > self.star_reverse_duration * 0.33:
                            star_anim_img = self.star_bullet_img_1
                        if dt > self.star_reverse_duration * 0.66:
                            star_anim_img = self.star_bullet_img_2
                        if dt > self.star_reverse_duration * 0.9:
                            star_anim_img = self.star_bullet_img_3
                        self.screen.blit(star_anim_img, (int(bullet['x'] - star_anim_img.get_width() // 2), int(bullet['y'] - star_anim_img.get_height() // 2)))
                # Draw starchilds
                for sc in self.starchilds:
                    if now >= sc['spawn_time']:
                        sc['x'] += sc['vx'] / 60.0
                        sc['y'] += sc['vy'] / 60.0
                        # Select the correct image and rotation
                        if sc['img'] == 'up':
                            base_img = self.starchild_img_up
                        else:
                            base_img = self.starchild_img_down
                        rotated_img = pygame.transform.rotate(base_img, sc['angle'])
                        rect = rotated_img.get_rect(center=(int(sc['x']), int(sc['y'])))
                        if self.screen_rect.colliderect(rect):
                            self.screen.blit(rotated_img, rect)
                        # Use full rect for hitbox
                        if rect.collidepoint(player_center):
                            hit_this_frame = True
                            break
                if reverse_elapsed >= self.star_reverse_duration and not self.starchilds_exploded:
                    # Only trigger starchild explosion once, after both phases are done
                    for bullet in self.star_bullets:
                        if not bullet.get('exploded'):
                            bullet['exploded'] = True
                            scx, scy = bullet['x'], bullet['y']
                            now_spawn = now
                            # Early group: up, down-right (down -45°), down-left (down +45°)
                            # up
                            self.starchilds.append({'x': scx, 'y': scy, 'vx': 0, 'vy': -self.starchild_speed, 'spawn_time': now_spawn + self.starchild_delay_early, 'img': 'up', 'angle': 0})
                            # down-right
                            angle = 45
                            vx = self.starchild_speed * math.sin(math.radians(45))
                            vy = self.starchild_speed * math.cos(math.radians(45))
                            self.starchilds.append({'x': scx, 'y': scy, 'vx': vx, 'vy': vy, 'spawn_time': now_spawn + self.starchild_delay_early, 'img': 'down', 'angle': angle})
                            # down-left
                            angle = -45
                            vx = -self.starchild_speed * math.sin(math.radians(45))
                            vy = self.starchild_speed * math.cos(math.radians(45))
                            self.starchilds.append({'x': scx, 'y': scy, 'vx': vx, 'vy': vy, 'spawn_time': now_spawn + self.starchild_delay_early, 'img': 'down', 'angle': angle})
                            # Late group: down, up-right (up +45°), up-left (up -45°)
                            # down
                            self.starchilds.append({'x': scx, 'y': scy, 'vx': 0, 'vy': self.starchild_speed, 'spawn_time': now_spawn + self.starchild_delay_late, 'img': 'down', 'angle': 0})
                            # up-right
                            angle = -45
                            vx = self.starchild_speed * math.sin(math.radians(45))
                            vy = -self.starchild_speed * math.cos(math.radians(45))
                            self.starchilds.append({'x': scx, 'y': scy, 'vx': vx, 'vy': vy, 'spawn_time': now_spawn + self.starchild_delay_late, 'img': 'up', 'angle': angle})
                            # up-left
                            angle = 45
                            vx = -self.starchild_speed * math.sin(math.radians(45))
                            vy = -self.starchild_speed * math.cos(math.radians(45))
                            self.starchilds.append({'x': scx, 'y': scy, 'vx': vx, 'vy': vy, 'spawn_time': now_spawn + self.starchild_delay_late, 'img': 'up', 'angle': angle})
                    self.starchilds_exploded = True
                    self.star_bullets.clear()
                    self.starchilds_display_start = now
                # After explosion, display starchilds for 1 second before switching to idle
                if self.starchilds_exploded and self.starchilds_display_start is not None:
                    if now - self.starchilds_display_start > 1500:
                        # Clear starchilds before switching to idle, before any drawing
                        self.starchilds.clear()
                        self.attack_phase = 'idle'
            elif self.attack_phase == 'idle':
                self.knight_idle_allowed = True
                if not self.idle_redraw_once:
                    draw_main_scene(
                        self.screen, self.bg_img, self.fountain_scaled_frames, self.fountain_frame_idx,
                        self.kris_idle_frames, self.kris_frame_idx, self.kris_rect,
                        self.susie_idle_frames, self.susie_frame_idx, self.susie_rect,
                        self.ralsei_idle_frames, self.ralsei_frame_idx, self.ralsei_rect,
                        self.battle_box_rect, self.battle_box_color, self.battle_box_border_color, self.battle_box_border,
                        self.heart_img_0, self.heart_img_1, self.player_x, self.player_y, self.heart_size, self.font, self.player_lives, False
                    )
                    pygame.display.flip()
                    self.idle_redraw_once = True
                if self.knight_idle_allowed:
                    # Only draw the idle Knight and its trail if attack_phase == 'idle'
                    float_offset = int(20 * math.sin(pygame.time.get_ticks() / 267))
                    knight_idle_rect = self.knight_idle_img.get_rect()
                    knight_idle_rect.centery = self.kris_rect.centery + 20  # 20px lower than Kris
                    knight_idle_rect.left = self.battle_box_rect.right + 40
                    knight_idle_rect.top += float_offset
                    trail_img = self.knight_idle_img.copy()
                    trail_img.set_alpha(50)  # Adjust for desired faintness
                    trail_rect = knight_idle_rect.copy()
                    trail_rect.left += 40  # Adjust offset as desired
                    self.screen.blit(trail_img, trail_rect)

                    # Insert the current state at the start of the trail
                    knight_trail.insert(0, (self.knight_idle_img.copy(), knight_idle_rect.copy()))
                    if len(knight_trail) > trail_length:
                        knight_trail.pop()

                    # Draw the trail (oldest last, most faded)
                    for i, (img, rect) in enumerate(reversed(knight_trail)):
                        img = img.copy()
                        img.set_alpha(trail_alphas[i])
                        rect = rect.copy()
                        rect.left += 40 + i * 10  # Each copy further to the right for a wave effect
                        self.screen.blit(img, rect)
                    # Draw the main Knight sprite LAST
                    self.screen.blit(self.knight_idle_img, knight_idle_rect)

            pygame.display.flip()

            # Advance fountain frame
            self.fountain_anim_timer += 1
            if self.fountain_anim_timer >= self.fountain_anim_speed:
                self.fountain_frame_idx = (self.fountain_frame_idx + 1) % self.fountain_frame_count
                self.fountain_anim_timer = 0

            # Advance Kris idle frame
            self.kris_anim_timer += 1
            if self.kris_anim_timer >= self.kris_anim_speed:
                self.kris_frame_idx = (self.kris_frame_idx + 1) % self.kris_frame_count
                self.kris_anim_timer = 0

            # Advance Susie idle frame
            self.susie_anim_timer += 1
            if self.susie_anim_timer >= self.susie_anim_speed:
                self.susie_frame_idx = (self.susie_frame_idx + 1) % self.susie_frame_count
                self.susie_anim_timer = 0

            # Advance Ralsei idle frame
            self.ralsei_anim_timer += 1
            if self.ralsei_anim_timer >= self.ralsei_anim_speed:
                self.ralsei_frame_idx = (self.ralsei_frame_idx + 1) % self.ralsei_frame_count
                self.ralsei_anim_timer = 0

            self.clock.tick(60)  # 60 FPS

            # If the attack phase is 'idle' and the idle redraw has happened, end the loop
            if self.attack_phase == 'idle' and self.idle_redraw_once:
                running = False

def PreAttack2(
    screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
    kris_idle_frames, kris_frame_idx, kris_rect,
    susie_idle_frames, susie_frame_idx, susie_rect,
    ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
    battle_box_rect, original_battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
    heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
    knight_idle_img, show_knight_idle, clock,
    knight_idle_left, knight_idle_centery,
    anim_duration=2000, player_speed=5
):
    """
    Smoothly move and resize the battle box to its original center and make it a perfect square (width=height)
    over anim_duration ms, while drawing the idle scene and allowing player movement.
    Returns the updated battle box rect and player position.
    """
    start_time = pygame.time.get_ticks()
    start_rect = battle_box_rect.copy()
    end_center = original_battle_box_rect.center
    target_size = (start_rect.height, start_rect.height)  # perfect square
    running = True
    fountain_anim_timer = 0
    kris_anim_timer = 0
    susie_anim_timer = 0
    ralsei_anim_timer = 0
    while running:
        now = pygame.time.get_ticks()
        t = min((now - start_time) / anim_duration, 1.0)
        # Advance animation frames
        fountain_anim_timer += 1
        if fountain_anim_timer >= 16:
            fountain_frame_idx = (fountain_frame_idx + 1) % len(fountain_scaled_frames)
            fountain_anim_timer = 0
        kris_anim_timer += 1
        if kris_anim_timer >= 8:
            kris_frame_idx = (kris_frame_idx + 1) % len(kris_idle_frames)
            kris_anim_timer = 0
        susie_anim_timer += 1
        if susie_anim_timer >= 8:
            susie_frame_idx = (susie_frame_idx + 1) % len(susie_idle_frames)
            susie_anim_timer = 0
        ralsei_anim_timer += 1
        if ralsei_anim_timer >= 8:
            ralsei_frame_idx = (ralsei_frame_idx + 1) % len(ralsei_idle_frames)
            ralsei_anim_timer = 0
        # Interpolate center
        new_center_x = int(start_rect.centerx + (end_center[0] - start_rect.centerx) * t)
        new_center_y = int(start_rect.centery + (end_center[1] - start_rect.centery) * t)
        # Interpolate width
        new_width = int(start_rect.width + (target_size[0] - start_rect.width) * t)
        new_height = start_rect.height  # height stays the same
        # Make it a perfect square
        new_width = new_height
        # Build new rect
        new_rect = pygame.Rect(0, 0, new_width, new_height)
        new_rect.center = (new_center_x, new_center_y)
        # Handle player movement
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                sys.exit()
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            player_x -= player_speed
        if keys[pygame.K_RIGHT]:
            player_x += player_speed
        if keys[pygame.K_UP]:
            player_y -= player_speed
        if keys[pygame.K_DOWN]:
            player_y += player_speed
        # Clamp player position to inside the new battle box
        playable_rect = new_rect.inflate(-2 * battle_box_border, -2 * battle_box_border)
        player_x = max(playable_rect.left, min(player_x, playable_rect.right - heart_size))
        player_y = max(playable_rect.top, min(player_y, playable_rect.bottom - heart_size))
        # Draw the idle scene with the new battle box
        draw_main_scene(
            screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
            kris_idle_frames, kris_frame_idx, kris_rect,
            susie_idle_frames, susie_frame_idx, susie_rect,
            ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
            new_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
            knight_idle_img, show_knight_idle, clock,
            knight_idle_left, knight_idle_centery
        )
        pygame.display.flip()
        clock.tick(60)
        if t >= 1.0:
            running = False
    return new_rect, player_x, player_y

def PreAttack3(
    screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
    kris_idle_frames, kris_frame_idx, kris_rect,
    susie_idle_frames, susie_frame_idx, susie_rect,
    ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
    battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
    heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
    knight_idle_img, show_knight_idle, clock,
    knight_idle_left=None, knight_idle_centery=None,
    anim_duration=2000, player_speed=5
):
    """
    Smoothly resize the battle box back to 450x300 px and center, over anim_duration ms, updating the idle scene.
    Returns the updated battle box rect and player position.
    """
    start_time = pygame.time.get_ticks()
    start_rect = battle_box_rect.copy()
    # Target: 450x300 px, centered as in original setup
    screen_width, screen_height = screen.get_width(), screen.get_height()
    target_width, target_height = 450, 300
    target_left = (screen_width - target_width) // 2 + 50
    target_top = (screen_height - target_height) // 2 + 20
    target_rect = pygame.Rect(target_left, target_top, target_width, target_height)
    running = True
    fountain_anim_timer = 0
    kris_anim_timer = 0
    susie_anim_timer = 0
    ralsei_anim_timer = 0
    while running:
        now = pygame.time.get_ticks()
        t = min((now - start_time) / anim_duration, 1.0)
        # Advance animation frames
        fountain_anim_timer += 1
        if fountain_anim_timer >= 16:
            fountain_frame_idx = (fountain_frame_idx + 1) % len(fountain_scaled_frames)
            fountain_anim_timer = 0
        kris_anim_timer += 1
        if kris_anim_timer >= 8:
            kris_frame_idx = (kris_frame_idx + 1) % len(kris_idle_frames)
            kris_anim_timer = 0
        susie_anim_timer += 1
        if susie_anim_timer >= 8:
            susie_frame_idx = (susie_frame_idx + 1) % len(susie_idle_frames)
            susie_anim_timer = 0
        ralsei_anim_timer += 1
        if ralsei_anim_timer >= 8:
            ralsei_frame_idx = (ralsei_frame_idx + 1) % len(ralsei_idle_frames)
            ralsei_anim_timer = 0
        # Interpolate position and size
        new_left = int(start_rect.left + (target_rect.left - start_rect.left) * t)
        new_top = int(start_rect.top + (target_rect.top - start_rect.top) * t)
        new_width = int(start_rect.width + (target_rect.width - start_rect.width) * t)
        new_height = int(start_rect.height + (target_rect.height - start_rect.height) * t)
        new_rect = pygame.Rect(new_left, new_top, new_width, new_height)
        # Handle player movement
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                sys.exit()
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            player_x -= player_speed
        if keys[pygame.K_RIGHT]:
            player_x += player_speed
        if keys[pygame.K_UP]:
            player_y -= player_speed
        if keys[pygame.K_DOWN]:
            player_y += player_speed
        # Clamp player position to inside the new battle box
        playable_rect = new_rect.inflate(-2 * battle_box_border, -2 * battle_box_border)
        player_x = max(playable_rect.left, min(player_x, playable_rect.right - heart_size))
        player_y = max(playable_rect.top, min(player_y, playable_rect.bottom - heart_size))
        # Draw the idle scene with the new battle box
        draw_main_scene(
            screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
            kris_idle_frames, kris_frame_idx, kris_rect,
            susie_idle_frames, susie_frame_idx, susie_rect,
            ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
            new_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
            knight_idle_img, show_knight_idle, clock,
            knight_idle_left, knight_idle_centery
        )
        pygame.display.flip()
        clock.tick(60)
        if t >= 1.0:
            running = False
    return new_rect, player_x, player_y

def PreAttack5(
    screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
    kris_idle_frames, kris_frame_idx, kris_rect,
    susie_idle_frames, susie_frame_idx, susie_rect,
    ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
    battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
    heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
    knight_idle_img, show_knight_idle, clock,
    knight_idle_left=None, knight_idle_centery=None,
    anim_duration=2000, player_speed=5
):
    """
    Smoothly resize the battle box to a perfect square (width=height) and center it,
    over anim_duration ms, updating the idle scene.
    Returns the updated battle box rect and player position.
    """
    start_time = pygame.time.get_ticks()
    start_rect = battle_box_rect.copy()
    # Target: perfect square, centered
    screen_width, screen_height = screen.get_width(), screen.get_height()
    target_size = min(start_rect.width, start_rect.height)  # Use the smaller dimension
    target_left = (screen_width - target_size) // 2 + 50
    target_top = (screen_height - target_size) // 2 + 20
    target_rect = pygame.Rect(target_left, target_top, target_size, target_size)
    running = True
    fountain_anim_timer = 0
    kris_anim_timer = 0
    susie_anim_timer = 0
    ralsei_anim_timer = 0
    while running:
        now = pygame.time.get_ticks()
        t = min((now - start_time) / anim_duration, 1.0)
        # Advance animation frames
        fountain_anim_timer += 1
        if fountain_anim_timer >= 16:
            fountain_frame_idx = (fountain_frame_idx + 1) % len(fountain_scaled_frames)
            fountain_anim_timer = 0
        kris_anim_timer += 1
        if kris_anim_timer >= 8:
            kris_frame_idx = (kris_frame_idx + 1) % len(kris_idle_frames)
            kris_anim_timer = 0
        susie_anim_timer += 1
        if susie_anim_timer >= 8:
            susie_frame_idx = (susie_frame_idx + 1) % len(susie_idle_frames)
            susie_anim_timer = 0
        ralsei_anim_timer += 1
        if ralsei_anim_timer >= 8:
            ralsei_frame_idx = (ralsei_frame_idx + 1) % len(ralsei_idle_frames)
            ralsei_anim_timer = 0
        # Interpolate position and size
        new_left = int(start_rect.left + (target_rect.left - start_rect.left) * t)
        new_top = int(start_rect.top + (target_rect.top - start_rect.top) * t)
        new_width = int(start_rect.width + (target_rect.width - start_rect.width) * t)
        new_height = int(start_rect.height + (target_rect.height - start_rect.height) * t)
        new_rect = pygame.Rect(new_left, new_top, new_width, new_height)
        # Handle player movement
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                sys.exit()
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            player_x -= player_speed
        if keys[pygame.K_RIGHT]:
            player_x += player_speed
        if keys[pygame.K_UP]:
            player_y -= player_speed
        if keys[pygame.K_DOWN]:
            player_y += player_speed
        # Clamp player position to inside the new battle box
        playable_rect = new_rect.inflate(-2 * battle_box_border, -2 * battle_box_border)
        player_x = max(playable_rect.left, min(player_x, playable_rect.right - heart_size))
        player_y = max(playable_rect.top, min(player_y, playable_rect.bottom - heart_size))
        # Draw the idle scene with the new battle box
        draw_main_scene(
            screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
            kris_idle_frames, kris_frame_idx, kris_rect,
            susie_idle_frames, susie_frame_idx, susie_rect,
            ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
            new_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
            knight_idle_img, show_knight_idle, clock,
            knight_idle_left, knight_idle_centery
        )
        pygame.display.flip()
        clock.tick(60)
        if t >= 1.0:
            running = False
    return new_rect, player_x, player_y

def draw_main_scene(
    screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
    kris_idle_frames, kris_frame_idx, kris_rect,
    susie_idle_frames, susie_frame_idx, susie_rect,
    ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
    battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
    heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
    knight_idle_img=None, show_knight_idle=True, clock=None,
    knight_idle_left=None, knight_idle_centery=None
):  
    if not hasattr(draw_main_scene, "music_started"):
        pygame.mixer.music.load(os.path.join('black_knife.ogg'))
        pygame.mixer.music.play(-1)  
        draw_main_scene.music_started = True
    global knight_trail, trail_length, trail_alphas
    # Draw background
    bg_img_scaled = pygame.transform.scale(bg_img, (screen.get_width(), screen.get_height()))
    screen.blit(bg_img_scaled, (0, 0))
    # Draw Kris
    kris_img = kris_idle_frames[kris_frame_idx]
    kris_rect_draw = kris_rect.copy()
    screen.blit(kris_img, kris_rect_draw)
    # Draw fountain
    fountain_img = fountain_scaled_frames[fountain_frame_idx]
    fountain_rect = fountain_img.get_rect()
    fountain_rect.left = kris_rect.left + kris_img.get_width() + 100
    fountain_rect.top = 0
    screen.blit(fountain_img, fountain_rect)
    # Draw Susie
    susie_img = susie_idle_frames[susie_frame_idx]
    susie_rect_draw = susie_img.get_rect()
    susie_rect_draw.left = kris_rect_draw.left - 120
    susie_rect_draw.centery = kris_rect_draw.centery + 100  
    screen.blit(susie_img, susie_rect_draw)
    # Draw Ralsei
    ralsei_img = ralsei_idle_frames[ralsei_frame_idx]
    ralsei_rect_draw = ralsei_img.get_rect()
    ralsei_rect_draw.left = susie_rect_draw.left - 10
    ralsei_rect_draw.centery = susie_rect_draw.centery + 100
    screen.blit(ralsei_img, ralsei_rect_draw)
    # Draw battle box
    pygame.draw.rect(screen, battle_box_color, battle_box_rect)
    pygame.draw.rect(screen, battle_box_border_color, battle_box_rect, battle_box_border)
    # Draw player heart (flashing if invincible)
    if invincible:
        if ((pygame.time.get_ticks() // 100) % 2) == 0:
            heart_draw_img = heart_img_0
        else:
            heart_draw_img = heart_img_1
    else:
        heart_draw_img = heart_img_0
    screen.blit(heart_draw_img, (player_x, player_y))
   # Draw lives counter
    if font is not None:
        lives_surf = font.render(f"LIVES: {player_lives}", True, (255, 255, 255))
        screen.blit(lives_surf, (50, 50))
    # Draw Knight idle animation and trail if enabled
    if show_knight_idle and knight_idle_img is not None:
        float_offset = int(20 * math.sin(pygame.time.get_ticks() / 267))
        knight_idle_rect = knight_idle_img.get_rect()
        if knight_idle_left is not None and knight_idle_centery is not None:
            knight_idle_rect.left = knight_idle_left
            knight_idle_rect.centery = knight_idle_centery
        else:
            knight_idle_rect.centery = kris_rect_draw.centery + 20
            knight_idle_rect.left = battle_box_rect.right + 40
        knight_idle_rect.top += float_offset
        trail_img = knight_idle_img.copy()
        trail_img.set_alpha(50)
        trail_rect = knight_idle_rect.copy()
        trail_rect.left += 40
        screen.blit(trail_img, trail_rect)
        # Insert the current state at the start of the trail
        knight_trail.insert(0, (knight_idle_img.copy(), knight_idle_rect.copy()))
        if len(knight_trail) > trail_length:
            knight_trail.pop()
        # Draw the trail (oldest last, most faded)
        for i, (img, rect) in enumerate(reversed(knight_trail)):
            img = img.copy()
            img.set_alpha(trail_alphas[i])
            rect = rect.copy()
            rect.left += 40 + i * 10
            screen.blit(img, rect)
        # Draw the main Knight sprite LAST
        screen.blit(knight_idle_img, knight_idle_rect)

class Attack2:
    def __init__(self, screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
    kris_idle_frames, kris_frame_idx, kris_rect,
    susie_idle_frames, susie_frame_idx, susie_rect,
    ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
    battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
    heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives,
    clock, player_speed, base_dir, knight_idle_img,
    fountain_anim_speed=16, fountain_frame_count=4,
    kris_anim_speed=8, kris_frame_count=None,
    susie_anim_speed=8, susie_frame_count=None,
                 ralsei_anim_speed=8, ralsei_frame_count=None, show_wheel=False):
        
        self.screen = screen
        self.bg_img = bg_img
        self.fountain_scaled_frames = fountain_scaled_frames
        self.fountain_frame_idx = fountain_frame_idx
        self.kris_idle_frames = kris_idle_frames
        self.kris_frame_idx = kris_frame_idx
        self.kris_rect = kris_rect
        self.susie_idle_frames = susie_idle_frames
        self.susie_frame_idx = susie_frame_idx
        self.susie_rect = susie_rect
        self.ralsei_idle_frames = ralsei_idle_frames
        self.ralsei_frame_idx = ralsei_frame_idx
        self.ralsei_rect = ralsei_rect
        self.battle_box_rect = battle_box_rect
        self.battle_box_color = battle_box_color
        self.battle_box_border_color = battle_box_border_color
        self.battle_box_border = battle_box_border
        self.heart_img_0 = heart_img_0
        self.heart_img_1 = heart_img_1
        self.player_x = player_x
        self.player_y = player_y
        self.heart_size = heart_size
        self.font = font
        self.player_lives = player_lives
        self.clock = clock
        self.player_speed = player_speed
        self.base_dir = base_dir
        self.knight_idle_img = knight_idle_img
        
        # Animation settings
        self.fountain_anim_speed = fountain_anim_speed
        self.fountain_frame_count = fountain_frame_count
        self.kris_anim_speed = kris_anim_speed
        self.kris_frame_count = kris_frame_count or len(kris_idle_frames)
        self.susie_anim_speed = susie_anim_speed
        self.susie_frame_count = susie_frame_count or len(susie_idle_frames)
        self.ralsei_anim_speed = ralsei_anim_speed
        self.ralsei_frame_count = ralsei_frame_count or len(ralsei_idle_frames)
        
        # Attack state
        self.state = 'running'
        self.invincible_until = 0
        
        # Wheel properties (must be set before load_assets)
        self.show_wheel = show_wheel
        self.wheel_base_img = None
        self.wheel_angle = 0.0  # in degrees
        self.wheel_pos = None
        self.wheel_target_pos = None
        if self.show_wheel:
            center = (self.player_x + self.heart_size // 2, self.player_y + self.heart_size // 2)
            self.wheel_pos = list(center)
            self.wheel_target_pos = list(center)
            self.wheel_slide_timer = 0
            self.wheel_slide_interval = 1000  # ms
            self.wheel_slide_duration = 200   # ms
            self.wheel_slide_progress = 1.0   # 1.0 = at target
        
        # Load assets
        self.load_assets()
        
        # Initialize attack variables
        self.swords = []
        self.attack_duration = 7000  # ms
        self.sword_interval = 700  # ms
        self.start_time = pygame.time.get_ticks()
        self.next_sword_time = self.start_time
        self.sword_idx = 0
        self.num_swords = 8
        self.directions = ['up', 'down', 'left', 'right']
        self.spawn_sides = []
        
        # Animation timers
        self.fountain_anim_timer = 0
        self.kris_anim_timer = 0
        self.susie_anim_timer = 0
        self.ralsei_anim_timer = 0
    
    def load_assets(self):
        # Load sword sprites
        self.sword_imgs = {
            'up': pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_sword', 'spr_knight_sword_up.png')).convert_alpha(),
            'down': pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_sword', 'spr_knight_sword_down.png')).convert_alpha(),
            'left': pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_sword', 'spr_knight_sword_left.png')).convert_alpha(),
            'right': pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_sword', 'spr_knight_sword_right.png')).convert_alpha(),
        }
        self.sword_imgs_red = {
            'up': pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_sword', 'spr_knight_sword_up_red.png')).convert_alpha(),
            'down': pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_sword', 'spr_knight_sword_down_red.png')).convert_alpha(),
            'left': pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_sword', 'spr_knight_sword_left_red.png')).convert_alpha(),
            'right': pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_sword', 'spr_knight_sword_right_red.png')).convert_alpha(),
        }
        
        # Load sound
        self.sword_shoot_sfx = pygame.mixer.Sound(os.path.join(self.base_dir, 'sprites', 'sound_effects', 'sword_shoot.wav'))
        
        # Load sword slash sprites (vertical and horizontal)
        self.slash_img_vert = pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_sword_shoot', 'spr_rk_sword_shoot_vert.png')).convert_alpha()
        self.slash_img_horiz = pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_sword_shoot', 'spr_rk_sword_shoot_horiz.png')).convert_alpha()
        
        # Make swords larger
        sword_scale = 1.5
        for k in self.sword_imgs:
            w, h = self.sword_imgs[k].get_size()
            self.sword_imgs[k] = pygame.transform.smoothscale(self.sword_imgs[k], (int(w * sword_scale), int(h * sword_scale)))
            # Also scale the red versions
            w_red, h_red = self.sword_imgs_red[k].get_size()
            self.sword_imgs_red[k] = pygame.transform.smoothscale(self.sword_imgs_red[k], (int(w * sword_scale), int(h * sword_scale)))
        
        self.margin = int(0.5 * max(self.sword_imgs['up'].get_width(), self.sword_imgs['up'].get_height()))
        
        # Wheel asset loading
        if self.show_wheel:
            img_path = os.path.join(self.base_dir, 'sprites', 'spr_rk_swordwheel', 'spr_rk_swordwheel_0.png')
            img = pygame.image.load(img_path).convert_alpha()
            self.wheel_base_img = pygame.transform.smoothscale(img, (350, 350))
            self.wheel_frame_count = 1
            self.wheel_frame_idx = 0
            self.wheel_anim_timer = 0

    # Sword data structure
    class Sword:
        def __init__(self, attack2_instance, spawn_time, pos, direction):
            self.attack2 = attack2_instance
            self.spawn_time = spawn_time
            self.direction = direction
            self.timer = 0.0
            self.following = True
            self.shot = False
            self.removed = False
            self.line_img = None
            self.sword_img = None
            self.sword_img_red = None
            self.turned_red = False
            self.rect = None
            self.line_rect = None
            self.sound_played = False
            # Set sprite and slash
            if direction == 'up':
                self.sword_img = self.attack2.sword_imgs['up']
                self.sword_img_red = self.attack2.sword_imgs_red['up']
                self.line_img = self.attack2.slash_img_horiz
                self.pos = list(pos)
            elif direction == 'down':
                self.sword_img = self.attack2.sword_imgs['down']
                self.sword_img_red = self.attack2.sword_imgs_red['down']
                self.line_img = self.attack2.slash_img_horiz
                self.pos = list(pos)
            elif direction == 'left':
                self.sword_img = self.attack2.sword_imgs['left']
                self.sword_img_red = self.attack2.sword_imgs_red['left']
                self.line_img = self.attack2.slash_img_vert
                self.pos = list(pos)
            elif direction == 'right':
                self.sword_img = self.attack2.sword_imgs['right']
                self.sword_img_red = self.attack2.sword_imgs_red['right']
                self.line_img = self.attack2.slash_img_vert
                self.pos = list(pos)
            self.rect = self.sword_img.get_rect(center=self.pos)
            self.line_rect = self.line_img.get_rect(center=self.pos)
        def update(self, player_center, now, box, border):
            self.timer = (now - self.spawn_time) / 1000.0
            if self.timer < 0.7:
                if self.direction == 'up':
                    self.pos[0] = min(max(player_center[0], box.left + self.attack2.margin), box.right - self.attack2.margin)
                    self.pos[1] = box.bottom + self.attack2.margin
                elif self.direction == 'down':
                    self.pos[0] = min(max(player_center[0], box.left + self.attack2.margin), box.right - self.attack2.margin)
                    self.pos[1] = box.top - self.attack2.margin
                elif self.direction == 'left':
                    self.pos[0] = box.right + self.attack2.margin
                    self.pos[1] = min(max(player_center[1], box.top + self.attack2.margin), box.bottom - self.attack2.margin)
                elif self.direction == 'right':
                    self.pos[0] = box.left - self.attack2.margin
                    self.pos[1] = min(max(player_center[1], box.top + self.attack2.margin), box.bottom - self.attack2.margin)
            self.rect.center = self.pos
            self.line_rect.center = self.pos
        def turn_red(self):
            if not self.turned_red and self.sword_img_red is not None:
                self.sword_img = self.sword_img_red
                self.turned_red = True
        def draw(self, screen):
            screen.blit(self.sword_img, self.rect)
        def draw_line(self, screen, box, border):
            # Draw the slash from the sword's current position to the opposite border or corner
            if self.direction == 'up':
                x = int(self.pos[0])
                y0 = box.bottom
                y1 = box.top
                length = abs(y1 - y0)
                slash = pygame.transform.scale(self.attack2.slash_img_horiz, (1, length))
                screen.blit(slash, (x, y1))
            elif self.direction == 'down':
                x = int(self.pos[0])
                y0 = box.top
                y1 = box.bottom
                length = abs(y1 - y0)
                slash = pygame.transform.scale(self.attack2.slash_img_horiz, (1, length))
                screen.blit(slash, (x, y0))
            elif self.direction == 'left':
                y = int(self.pos[1])
                x0 = box.right
                x1 = box.left
                length = abs(x1 - x0)
                slash = pygame.transform.scale(self.attack2.slash_img_vert, (length, 1))
                screen.blit(slash, (x1, y))
            elif self.direction == 'right':
                y = int(self.pos[1])
                x0 = box.left
                x1 = box.right
                length = abs(x1 - x0)
                slash = pygame.transform.scale(self.attack2.slash_img_vert, (length, 1))
                screen.blit(slash, (x0, y))
    def handle_player_movement(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.player_x -= self.player_speed
        if keys[pygame.K_RIGHT]:
            self.player_x += self.player_speed
        if keys[pygame.K_UP]:
            self.player_y -= self.player_speed
        if keys[pygame.K_DOWN]:
            self.player_y += self.player_speed
        # Clamp player position to inside the battle box
        playable_rect = self.battle_box_rect.inflate(-2 * self.battle_box_border, -2 * self.battle_box_border)
        self.player_x = max(playable_rect.left, min(self.player_x, playable_rect.right - self.heart_size))
        self.player_y = max(playable_rect.top, min(self.player_y, playable_rect.bottom - self.heart_size))

    def update(self, dt):
        now = pygame.time.get_ticks()
        
        # Advance animation timers and frame indices
        self.fountain_anim_timer += 1
        if self.fountain_anim_timer >= self.fountain_anim_speed:
            self.fountain_frame_idx = (self.fountain_frame_idx + 1) % self.fountain_frame_count
            self.fountain_anim_timer = 0
        self.kris_anim_timer += 1
        if self.kris_anim_timer >= self.kris_anim_speed:
            self.kris_frame_idx = (self.kris_frame_idx + 1) % self.kris_frame_count
            self.kris_anim_timer = 0
        self.susie_anim_timer += 1
        if self.susie_anim_timer >= self.susie_anim_speed:
            self.susie_frame_idx = (self.susie_frame_idx + 1) % self.susie_frame_count
            self.susie_anim_timer = 0
        self.ralsei_anim_timer += 1
        if self.ralsei_anim_timer >= self.ralsei_anim_speed:
            self.ralsei_frame_idx = (self.ralsei_frame_idx + 1) % self.ralsei_frame_count
            self.ralsei_anim_timer = 0
        
        # Spawn swords
        # Prepare a shuffled, non-repeating side list for sword spawns
        if self.sword_idx == 0:
            self.spawn_sides = []
            last_side = None
            while len(self.spawn_sides) < self.num_swords:
                side = random.choice(self.directions)
                if side != last_side:
                    self.spawn_sides.append(side)
                    last_side = side
        
        if self.sword_idx < self.num_swords and now >= self.next_sword_time:
            side = self.spawn_sides[self.sword_idx]
            # Pick a random offset along the side (avoid edges)
            if side == 'up':
                offset = random.randint(30, self.battle_box_rect.width - 30)
                pos = (self.battle_box_rect.left + offset, self.battle_box_rect.top - self.margin)
            elif side == 'down':
                offset = random.randint(30, self.battle_box_rect.width - 30)
                pos = (self.battle_box_rect.left + offset, self.battle_box_rect.bottom + self.margin)
            elif side == 'left':
                offset = random.randint(30, self.battle_box_rect.height - 30)
                pos = (self.battle_box_rect.left - self.margin, self.battle_box_rect.top + offset)
            elif side == 'right':
                offset = random.randint(30, self.battle_box_rect.height - 30)
                pos = (self.battle_box_rect.right + self.margin, self.battle_box_rect.top + offset)
            self.swords.append(self.Sword(self, now, pos, side))
            self.sword_idx += 1
            self.next_sword_time += self.sword_interval
        
        # Update swords
        player_center = (self.player_x + self.heart_size // 2, self.player_y + self.heart_size // 2)
        for sword in self.swords:
            if sword.timer < 1.0:
                sword.update(player_center, now, self.battle_box_rect, self.battle_box_border)
                # Play sound and draw line at 0.8s
                if sword.timer >= 0.75 and not sword.sound_played:
                    sword.turn_red()
                    self.sword_shoot_sfx.play()
                    sword.sound_played = True
            else:
                sword.removed = True
        
        # Remove swords that are done
        self.swords = [s for s in self.swords if not s.removed]
        
        # Check if attack is done (all swords spawned and all swords removed)
        if self.sword_idx >= self.num_swords and len(self.swords) == 0:
            self.state = 'done'
        
        # Collision detection
        hit_this_frame = False
        player_rect = pygame.Rect(self.player_x, self.player_y, self.heart_size, self.heart_size)
        
        for sword in self.swords:
            if sword.rect.colliderect(player_rect):
                hit_this_frame = True
                break
            if sword.timer >= 0.9:
                # Make the slash hitbox larger
                if sword.direction in ('up', 'down'):
                    # Horizontal slash: much taller hitbox
                    slash_hitbox = pygame.Rect(
                        int(sword.pos[0]) - 24, self.battle_box_rect.top, 48, self.battle_box_rect.height
                    )
                elif sword.direction in ('left', 'right'):
                    # Vertical slash: much wider hitbox
                    slash_hitbox = pygame.Rect(
                        self.battle_box_rect.left, int(sword.pos[1]) - 24, self.battle_box_rect.width, 48
                    )
                if slash_hitbox.colliderect(player_rect):
                    hit_this_frame = True
                    break
        # Sword wheel collision (Attack8/Attack2 with show_wheel)
        if self.show_wheel:
            # Rotate wheel
            rotated = pygame.transform.rotate(self.wheel_base_img, self.wheel_angle)
            wheel_rect = rotated.get_rect(center=(int(self.wheel_pos[0]), int(self.wheel_pos[1])))

            # Get wheel center
            wheel_cx, wheel_cy = int(self.wheel_pos[0]), int(self.wheel_pos[1])
            player_cx = self.player_x + self.heart_size // 2
            player_cy = self.player_y + self.heart_size // 2

            # These should match the actual ring in your image!
            outer_radius = self.wheel_base_img.get_width() // 2 - 10  # -10 for padding
            inner_radius = outer_radius - 60  # adjust 60 to match the thickness of the sword ring

            dx = player_cx - wheel_cx
            dy = player_cy - wheel_cy
            dist_squared = dx * dx + dy * dy

            if inner_radius ** 2 < dist_squared < outer_radius ** 2:
                hit_this_frame = True
        
        # Invincibility logic
        if pygame.time.get_ticks() < self.invincible_until:
            invincible = True
        else:
            invincible = False
        if hit_this_frame and not invincible:
            self.player_lives = max(0, self.player_lives - 1)
            self.invincible_until = pygame.time.get_ticks() + 1000  # 1 second invincibility
        
        # --- Wheel animation and follow logic ---
        if self.show_wheel:
            # Rotate wheel by 6 degrees per frame
            self.wheel_angle = (self.wheel_angle - 4) % 360

            # --- Follow logic ---
            player_center = [self.player_x + self.heart_size // 2, self.player_y + self.heart_size // 2]
            max_move = 0.4 * self.player_speed
            dx = player_center[0] - self.wheel_pos[0]
            dy = player_center[1] - self.wheel_pos[1]
            dist = (dx ** 2 + dy ** 2) ** 0.5
            if dist > 1e-3:
                move_dist = min(dist, max_move)
                self.wheel_pos[0] += dx / dist * move_dist
                self.wheel_pos[1] += dy / dist * move_dist

    def draw(self):
        # Draw background
        bg_img_scaled = pygame.transform.scale(self.bg_img, (self.screen.get_width(), self.screen.get_height()))
        self.screen.blit(bg_img_scaled, (0, 0))
        
        # Draw scene (heroes, box, etc.)
        draw_main_scene(
            self.screen, self.bg_img, self.fountain_scaled_frames, self.fountain_frame_idx,
            self.kris_idle_frames, self.kris_frame_idx, self.kris_rect,
            self.susie_idle_frames, self.susie_frame_idx, self.susie_rect,
            self.ralsei_idle_frames, self.ralsei_frame_idx, self.ralsei_rect,
            self.battle_box_rect, self.battle_box_color, self.battle_box_border_color, self.battle_box_border,
            self.heart_img_0, self.heart_img_1, self.player_x, self.player_y, self.heart_size, self.font, self.player_lives, False
        )
        
        # --- Knight idle animation and trail (added for Attack2) ---
        float_offset = int(20 * math.sin(pygame.time.get_ticks() / 267))
        knight_idle_rect = self.knight_idle_img.get_rect()
        knight_idle_rect.centery = self.kris_rect.centery + 20
        knight_idle_rect.left = self.battle_box_rect.right + 40
        knight_idle_rect.top += float_offset
        trail_img = self.knight_idle_img.copy()
        trail_img.set_alpha(50)
        trail_rect = knight_idle_rect.copy()
        trail_rect.left += 40
        self.screen.blit(trail_img, trail_rect)
        
        # Note: knight_trail and trail_alphas are global variables, so we need to access them
        global knight_trail, trail_length, trail_alphas
        knight_trail.insert(0, (self.knight_idle_img.copy(), knight_idle_rect.copy()))
        if len(knight_trail) > trail_length:
            knight_trail.pop()
        for i, (img, rect) in enumerate(reversed(knight_trail)):
            img = img.copy()
            img.set_alpha(trail_alphas[i])
            rect = rect.copy()
            rect.left += 40 + i * 10
            self.screen.blit(img, rect)
        self.screen.blit(self.knight_idle_img, knight_idle_rect)
        # --- End knight idle animation and trail ---
        
        # Draw swords and lines
        for sword in self.swords:
            if sword.timer < 1.0:
                sword.draw(self.screen)
                if sword.timer >= 0.9:
                    sword.draw_line(self.screen, self.battle_box_rect, self.battle_box_border)
        
        # Draw lives counter
        lives_surf = self.font.render(f"LIVES: {self.player_lives}", True, (255, 255, 255))
        self.screen.blit(lives_surf, (50, 50))
        
        # Draw player heart (flashing if invincible)
        if pygame.time.get_ticks() < self.invincible_until:
            if ((pygame.time.get_ticks() // 100) % 2) == 0:
                heart_draw_img = self.heart_img_0
            else:
                heart_draw_img = self.heart_img_1
        else:
            heart_draw_img = self.heart_img_0
        self.screen.blit(heart_draw_img, (self.player_x, self.player_y))
        
        # --- Wheel drawing ---
        if self.show_wheel:
            rotated = pygame.transform.rotate(self.wheel_base_img, self.wheel_angle)
            wheel_rect = rotated.get_rect(center=(int(self.wheel_pos[0]), int(self.wheel_pos[1])))
            self.screen.blit(rotated, wheel_rect)
            

        
        pygame.display.flip()

    def run(self):
        running = True
        while self.state != 'done' and running:
            dt = self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit()
            
            self.handle_player_movement()
            self.update(dt)
            self.draw()

    def is_done(self):
        return self.state == 'done'

class Attack3:
    def __init__(self, screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
                 kris_idle_frames, kris_frame_idx, kris_rect,
                 susie_idle_frames, susie_frame_idx, susie_rect,
                 ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
                 battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
                 heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
                 knight_idle_img, show_knight_idle, clock,
                 knight_trail, trail_length, trail_alphas,
                 cut_mode='vertical', cycles=7, base_dir=None, player_speed=1, cut_modes=None):
        self.screen = screen
        self.bg_img = bg_img
        self.fountain_scaled_frames = fountain_scaled_frames
        self.fountain_frame_idx = fountain_frame_idx
        self.kris_idle_frames = kris_idle_frames
        self.kris_frame_idx = kris_frame_idx
        self.kris_rect = kris_rect
        self.susie_idle_frames = susie_idle_frames
        self.susie_frame_idx = susie_frame_idx
        self.susie_rect = susie_rect
        self.ralsei_idle_frames = ralsei_idle_frames
        self.ralsei_frame_idx = ralsei_frame_idx
        self.ralsei_rect = ralsei_rect
        self.battle_box_rect = battle_box_rect.copy()
        self.battle_box_color = battle_box_color
        self.battle_box_border_color = battle_box_border_color
        self.battle_box_border = battle_box_border
        self.heart_img_0 = heart_img_0
        self.heart_img_1 = heart_img_1
        self.player_x = player_x
        self.player_y = player_y
        self.heart_size = heart_size
        self.font = font
        self.player_lives = player_lives
        self.invincible = invincible
        self.invincible_until = 0
        self.knight_idle_img = knight_idle_img
        self.show_knight_idle = show_knight_idle
        self.clock = clock
        self.knight_trail = knight_trail
        self.trail_length = trail_length
        self.trail_alphas = trail_alphas
        self.cut_mode = cut_mode
        self.cycles = cycles
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.state = 'knight_anim'
        self.state_timer = 0
        self.cycle_count = 0
        self.player_speed = player_speed
        # Handle cut_modes list for random slash directions
        self.cut_modes = cut_modes
        if self.cut_modes is None:
            # Default: all vertical cuts (for Attack3 compatibility)
            self.cut_modes = ['vertical'] * cycles
        self.load_assets()
        self.reset_state()
        self.box_cut_slash_sfx = pygame.mixer.Sound(os.path.join(self.base_dir, 'sprites', 'sound_effects', 'box_cut_slash.wav'))
        self.box_cut_slash_played = False

    def load_assets(self):
        # Knight attack animation (scale to idle size)
        knight_attack_dir = os.path.join(self.base_dir, 'sprites', 'spr_roaringknight_attack_ol_center')
        idle_size = self.knight_idle_img.get_size()
        self.knight_attack_frames = [pygame.transform.smoothscale(
            pygame.image.load(os.path.join(knight_attack_dir, f'spr_roaringknight_attack_ol_center_{i}.png')).convert_alpha(),
            idle_size) for i in range(6)]
        # Load both vertical and horizontal cut animations
        cut_dir_vert = os.path.join(self.base_dir, 'sprites', 'spr_knight_cut_box', 'spr_knight_cut_box_vert')
        cut_dir_horiz = os.path.join(self.base_dir, 'sprites', 'spr_knight_cut_box', 'spr_knight_cut_box_horiz')
        self.cut_frames_vert = [pygame.image.load(os.path.join(cut_dir_vert, f'spr_knight_cut_box_vert_{i}.png')).convert_alpha() for i in range(4)]
        self.cut_frames_horiz = [pygame.image.load(os.path.join(cut_dir_horiz, f'spr_knight_cut_box_horiz_{i}.png')).convert_alpha() for i in range(4)]
        # Set initial cut frames based on current mode
        self.cut_frames = self.cut_frames_vert if self.cut_mode == 'vertical' else self.cut_frames_horiz
        # Tooth bullets (scale 1.5x)
        tooth_dir = os.path.join(self.base_dir, 'sprites', 'spr_roaringknight_tooth')
        orig_left = pygame.image.load(os.path.join(tooth_dir, 'spr_roaringknight_tooth_left.png')).convert_alpha()
        orig_right = pygame.image.load(os.path.join(tooth_dir, 'spr_roaringknight_tooth_right.png')).convert_alpha()
        orig_up = pygame.image.load(os.path.join(tooth_dir, 'spr_roaringknight_tooth_up.png')).convert_alpha()
        orig_down = pygame.image.load(os.path.join(tooth_dir, 'spr_roaringknight_tooth_down.png')).convert_alpha()
        scale = 1.5
        self.tooth_left = pygame.transform.smoothscale(orig_left, (int(orig_left.get_width()*scale), int(orig_left.get_height()*scale)))
        self.tooth_right = pygame.transform.smoothscale(orig_right, (int(orig_right.get_width()*scale), int(orig_right.get_height()*scale)))
        self.tooth_up = pygame.transform.smoothscale(orig_up, (int(orig_up.get_width()*scale), int(orig_up.get_height()*scale)))
        self.tooth_down = pygame.transform.smoothscale(orig_down, (int(orig_down.get_width()*scale), int(orig_down.get_height()*scale)))

    def reset_state(self):
        self.state = 'knight_anim'
        self.state_timer = 0
        self.knight_frame_idx = 0
        self.cut_frame_idx = 0
        self.cut_anim_done = False
        self.split_boxes = None
        self.bullets = []
        self.box_move_timer = 0
        self.box_merge_timer = 0
        self.wait_timer = 0
        self.player_in_left = True
        self.boxes = None
        self.bullets_spawned = False
        self.boxes_merging = False
        self.battle_box_rect = self.battle_box_rect.copy()
        # Set current cut mode based on cycle count
        if self.cycle_count < len(self.cut_modes):
            self.cut_mode = self.cut_modes[self.cycle_count]
            # Update cut frames based on current mode
            self.cut_frames = self.cut_frames_vert if self.cut_mode == 'vertical' else self.cut_frames_horiz
        # Don't reset player_x/y so movement is preserved
        self.box_cut_slash_played = False  # Reset sound flag for each slash

    def handle_player_movement(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.player_x -= self.player_speed
        if keys[pygame.K_RIGHT]:
            self.player_x += self.player_speed
        if keys[pygame.K_UP]:
            self.player_y -= self.player_speed
        if keys[pygame.K_DOWN]:
            self.player_y += self.player_speed
        # Clamp to current playable area
        if self.state in ('box_move', 'bullets') and self.boxes:
            playable_rect = self.boxes[0] if self.player_in_left else self.boxes[1]
        else:
            playable_rect = self.battle_box_rect
        playable_rect = playable_rect.inflate(-2 * self.battle_box_border, -2 * self.battle_box_border)
        self.player_x = max(playable_rect.left, min(self.player_x, playable_rect.right - self.heart_size))
        self.player_y = max(playable_rect.top, min(self.player_y, playable_rect.bottom - self.heart_size))

    def update(self, dt):
        self.state_timer += dt
        self.handle_player_movement()  # Always allow movement, every frame, every state
        # --- Bullet collision with player ---
        now = pygame.time.get_ticks()
        if self.state in ('box_move', 'bullets'):
            player_rect = pygame.Rect(self.player_x, self.player_y, self.heart_size, self.heart_size)
            for bullet in self.bullets:
                img_rect = bullet['img'].get_rect(topleft=(int(bullet['x']), int(bullet['y'])))
                # Shrink hitbox by 20% on each axis
                shrink_w = int(img_rect.width * 0.2)
                shrink_h = int(img_rect.height * 0.2)
                hitbox = img_rect.inflate(-shrink_w, -shrink_h)
                if player_rect.colliderect(hitbox):
                    if now > self.invincible_until:
                        self.player_lives = max(0, self.player_lives - 1)
                        self.invincible_until = now + 1000  # 1s invincibility
                        self.invincible = True
        if now > self.invincible_until:
            self.invincible = False
        # --- End bullet collision ---
        if self.state == 'knight_anim':
            frame_duration = 1000 // len(self.knight_attack_frames)
            self.knight_frame_idx = min(self.state_timer // frame_duration, len(self.knight_attack_frames) - 1)
            # Play slash sound at second last frame
            if (self.knight_frame_idx == len(self.knight_attack_frames) - 2) and not self.box_cut_slash_played:
                self.box_cut_slash_sfx.play()
                self.box_cut_slash_played = True
            if self.state_timer >= 1000:
                self.state = 'cut_anim'
                self.state_timer = 0
        elif self.state == 'cut_anim':
            frame_duration = 250 // len(self.cut_frames)
            self.cut_frame_idx = min(self.state_timer // frame_duration, len(self.cut_frames) - 1)
            if self.cut_frame_idx == 2 and not self.cut_anim_done:
                self.split_box()
                self.cut_anim_done = True
            if self.state_timer >= 250:
                self.state = 'box_move'
                self.state_timer = 0
        elif self.state == 'box_move':
            move_dist = 100
            move_time = 300
            t = min(self.state_timer / move_time, 1.0)
            if self.cut_mode == 'vertical':
                left_box, right_box = self.boxes
                left_box.left = self.battle_box_rect.left - int(move_dist * t)
                right_box.left = self.battle_box_rect.left + self.battle_box_rect.width // 2 + int(move_dist * t) + 50
            else:
                top_box, bottom_box = self.boxes
                top_box.top = self.battle_box_rect.top - int(move_dist * t)
                bottom_box.top = self.battle_box_rect.top + self.battle_box_rect.height // 2 + int(move_dist * t)
            if self.state_timer >= move_time:
                self.state = 'bullets'
                self.state_timer = 0
                self.spawn_bullets()
        elif self.state == 'bullets':
            for bullet in self.bullets:
                if 'vx' in bullet:
                    bullet['x'] += bullet['vx']
                else:
                    bullet['y'] += bullet['vy']
            merge_time = 600
            t = min(self.state_timer / merge_time, 1.0)
            move_dist = 100
            if self.cut_mode == 'vertical':
                left_box, right_box = self.boxes
                left_box.left = self.battle_box_rect.left - int(move_dist * (1-t))
                right_box.left = self.battle_box_rect.left + self.battle_box_rect.width // 2 + int(move_dist * (1-t))
            else:
                top_box, bottom_box = self.boxes
                top_box.top = self.battle_box_rect.top - int(move_dist * (1-t))
                bottom_box.top = self.battle_box_rect.top + self.battle_box_rect.height // 2 + int(move_dist * (1-t))
            
            # Check if merge animation is complete (t >= 1.0) or if boxes are close enough
            # Also add safety timeout to prevent getting stuck
            if t >= 1.0 or (self.cut_mode == 'vertical' and abs(left_box.right - right_box.left) <= 10) or (self.cut_mode == 'horizontal' and abs(top_box.bottom - bottom_box.top) <= 10) or self.state_timer >= 1000:
                self.state = 'merge'
                self.state_timer = 0
        elif self.state == 'merge':
            self.battle_box_rect = self.battle_box_rect.copy()
            self.state = 'wait'
            self.state_timer = 0
        elif self.state == 'wait':
            if self.state_timer >= 200:
                self.cycle_count += 1
                if self.cycle_count < self.cycles:
                    self.reset_state()
                else:
                    self.state = 'done'

    def split_box(self):
        if self.cut_mode == 'vertical':
            w, h = self.battle_box_rect.width, self.battle_box_rect.height
            left_box = pygame.Rect(self.battle_box_rect.left, self.battle_box_rect.top, w // 2, h)
            right_box = pygame.Rect(self.battle_box_rect.left + w // 2, self.battle_box_rect.top, w // 2, h)
            px = self.player_x + self.heart_size // 2
            if px < self.battle_box_rect.centerx:
                self.player_in_left = True
            else:
                self.player_in_left = False
            self.boxes = [left_box, right_box]
        else:
            w, h = self.battle_box_rect.width, self.battle_box_rect.height
            base_half_height = h // 2
            extra = 50  # amount to stretch each box
            new_half_height = base_half_height + extra

            # Keep the gap at the center the same by anchoring split at center
            center_y = self.battle_box_rect.centery

            # Top box: start above center and grow upward
            top_box_top = center_y - new_half_height
            top_box = pygame.Rect(self.battle_box_rect.left, top_box_top, w, new_half_height)

            # Bottom box: start at center and grow downward
            bottom_box_top = center_y
            bottom_box = pygame.Rect(self.battle_box_rect.left, bottom_box_top, w, new_half_height)

            py = self.player_y + self.heart_size // 2
            self.player_in_left = py < center_y
            self.boxes = [top_box, bottom_box]

            self.boxes = [top_box, bottom_box]
        playable_rect = self.boxes[0] if self.player_in_left else self.boxes[1]
        playable_rect = playable_rect.inflate(-2 * self.battle_box_border, -2 * self.battle_box_border)
        self.player_x = max(playable_rect.left, min(self.player_x, playable_rect.right - self.heart_size))
        self.player_y = max(playable_rect.top, min(self.player_y, playable_rect.bottom - self.heart_size))

    def spawn_bullets(self):
        self.bullets = []
        w, h = self.battle_box_rect.width, self.battle_box_rect.height
        if self.cut_mode == 'vertical':
            y_positions = [self.battle_box_rect.top + int(h * (i + 0.5) / 7) for i in range(7)]
            left_bullets = []
            right_bullets = []
            for y in y_positions:
                left_bullets.append({'x': self.boxes[0].right + 50, 'y': y, 'vx': -2.5, 'img': self.tooth_left})
                right_bullets.append({'x': self.boxes[1].left - 70, 'y': y, 'vx': 2.5, 'img': self.tooth_right})
            # Randomly pick 3 on each side to double speed
            left_fast = random.sample(range(7), 3)
            right_fast = random.sample(range(7), 3)
            for i in left_fast:
                left_bullets[i]['vx'] *= 3
            for i in right_fast:
                right_bullets[i]['vx'] *= 3
            self.bullets = left_bullets + right_bullets
        else:
            # For horizontal cuts, use up/down sprites
            x_positions = [self.battle_box_rect.left + int(w * (i + 0.5) / 7) for i in range(7)]
            top_bullets = []
            bottom_bullets = []
            for x in x_positions:
                top_bullets.append({'x': x, 'y': self.boxes[0].bottom + 50, 'vy': -2.5, 'img': self.tooth_up})
                bottom_bullets.append({'x': x, 'y': self.boxes[1].top - 50, 'vy': 2.5, 'img': self.tooth_down})
            top_fast = random.sample(range(7), 3)
            bottom_fast = random.sample(range(7), 3)
            for i in top_fast:
                top_bullets[i]['vy'] *= 3
            for i in bottom_fast:
                bottom_bullets[i]['vy'] *= 3
            self.bullets = top_bullets + bottom_bullets

    def run(self):
        # Main loop for the attack, handles events, player movement, and animation
        running = True
        # Animation timers for idle anims
        self.fountain_anim_timer = getattr(self, 'fountain_anim_timer', 0)
        self.kris_anim_timer = getattr(self, 'kris_anim_timer', 0)
        self.susie_anim_timer = getattr(self, 'susie_anim_timer', 0)
        self.ralsei_anim_timer = getattr(self, 'ralsei_anim_timer', 0)
        while not self.is_done() and running:
            dt = self.clock.tick(60)
            # --- Advance animation timers and frame indices ---
            self.fountain_anim_timer += 1
            if self.fountain_anim_timer >= 16:
                self.fountain_frame_idx = (self.fountain_frame_idx + 1) % len(self.fountain_scaled_frames)
                self.fountain_anim_timer = 0
            self.kris_anim_timer += 1
            if self.kris_anim_timer >= 8:
                self.kris_frame_idx = (self.kris_frame_idx + 1) % len(self.kris_idle_frames)
                self.kris_anim_timer = 0
            self.susie_anim_timer += 1
            if self.susie_anim_timer >= 8:
                self.susie_frame_idx = (self.susie_frame_idx + 1) % len(self.susie_idle_frames)
                self.susie_anim_timer = 0
            self.ralsei_anim_timer += 1
            if self.ralsei_anim_timer >= 8:
                self.ralsei_frame_idx = (self.ralsei_frame_idx + 1) % len(self.ralsei_idle_frames)
                self.ralsei_anim_timer = 0
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit()
            # Clamp to current playable area
            if self.state in ('box_move', 'bullets') and self.boxes:
                playable_rect = self.boxes[0] if self.player_in_left else self.boxes[1]
            else:
                playable_rect = self.battle_box_rect
            playable_rect = playable_rect.inflate(-2 * self.battle_box_border, -2 * self.battle_box_border)
            self.player_x = max(playable_rect.left, min(self.player_x, playable_rect.right - self.heart_size))
            self.player_y = max(playable_rect.top, min(self.player_y, playable_rect.bottom - self.heart_size))
            self.update(dt)
            self.draw()

    def draw(self):
        # Always draw the main scene (idle anims always play)
        # Hide the main battle box when in split state
        if self.state in ('box_move', 'bullets'):
            # Draw everything except the main battle box (draw_main_scene with a dummy rect offscreen)
            offscreen_rect = pygame.Rect(-10000, -10000, 1, 1)
            draw_main_scene(
                self.screen, self.bg_img, self.fountain_scaled_frames, self.fountain_frame_idx,
                self.kris_idle_frames, self.kris_frame_idx, self.kris_rect,
                self.susie_idle_frames, self.susie_frame_idx, self.susie_rect,
                self.ralsei_idle_frames, self.ralsei_frame_idx, self.ralsei_rect,
                offscreen_rect, self.battle_box_color, self.battle_box_border_color, self.battle_box_border,
                self.heart_img_0, self.heart_img_1, self.player_x, self.player_y, self.heart_size, self.font, self.player_lives, self.invincible,
                None, False, self.clock
            )
        else:
            draw_main_scene(
                self.screen, self.bg_img, self.fountain_scaled_frames, self.fountain_frame_idx,
                self.kris_idle_frames, self.kris_frame_idx, self.kris_rect,
                self.susie_idle_frames, self.susie_frame_idx, self.susie_rect,
                self.ralsei_idle_frames, self.ralsei_frame_idx, self.ralsei_rect,
                self.battle_box_rect, self.battle_box_color, self.battle_box_border_color, self.battle_box_border,
                self.heart_img_0, self.heart_img_1, self.player_x, self.player_y, self.heart_size, self.font, self.player_lives, self.invincible,
                None, False, self.clock
            )
        # Draw knight attack animation and trail (replace idle)
        if self.state == 'knight_anim':
            knight_img = self.knight_attack_frames[self.knight_frame_idx]
            knight_rect = knight_img.get_rect()
            knight_rect.left = self.battle_box_rect.right + 40
            knight_rect.centery = self.kris_rect.centery + 20
            self.knight_trail.insert(0, (knight_img.copy(), knight_rect.copy()))
            if len(self.knight_trail) > self.trail_length:
                self.knight_trail.pop()
            for i, (img, rect) in enumerate(reversed(self.knight_trail)):
                img = img.copy()
                img.set_alpha(self.trail_alphas[i])
                rect = rect.copy()
                rect.left += 40 + i * 10
                self.screen.blit(img, rect)
            self.screen.blit(knight_img, knight_rect)
        # Draw cut animation (thinner slash)
        if self.state == 'cut_anim':
            cut_img = self.cut_frames[self.cut_frame_idx]
            if self.cut_mode == 'vertical':
                scale_w = max(10, self.battle_box_rect.width // 4)
                scale_h = self.battle_box_rect.height
            else:
                scale_w = self.battle_box_rect.width
                scale_h = max(10, self.battle_box_rect.height // 4)
            cut_img = pygame.transform.smoothscale(cut_img, (scale_w, scale_h))
            cut_rect = cut_img.get_rect(center=self.battle_box_rect.center)
            self.screen.blit(cut_img, cut_rect)
        # Draw split boxes (no original box, correct borders)
        if self.state in ('box_move', 'bullets'):
            if self.cut_mode == 'vertical':
                left_box, right_box = self.boxes
                pygame.draw.rect(self.screen, self.battle_box_color, left_box)
                pygame.draw.rect(self.screen, self.battle_box_color, right_box)
                pygame.draw.rect(self.screen, self.battle_box_border_color, left_box, self.battle_box_border)
                pygame.draw.rect(self.screen, self.battle_box_border_color, right_box, self.battle_box_border)
                pygame.draw.line(self.screen, self.battle_box_color, left_box.topright, left_box.bottomright, self.battle_box_border)
                pygame.draw.line(self.screen, self.battle_box_color, right_box.topleft, right_box.bottomleft, self.battle_box_border)
            else:
                top_box, bottom_box = self.boxes
                pygame.draw.rect(self.screen, self.battle_box_color, top_box)
                pygame.draw.rect(self.screen, self.battle_box_color, bottom_box)
                pygame.draw.rect(self.screen, self.battle_box_border_color, top_box, self.battle_box_border)
                pygame.draw.rect(self.screen, self.battle_box_border_color, bottom_box, self.battle_box_border)
                pygame.draw.line(self.screen, self.battle_box_color, top_box.bottomleft, top_box.bottomright, self.battle_box_border)
                pygame.draw.line(self.screen, self.battle_box_color, bottom_box.topleft, bottom_box.topright, self.battle_box_border)
            self.screen.blit(self.heart_img_0, (self.player_x, self.player_y))
            for bullet in self.bullets:
                if 'vx' in bullet:
                    self.screen.blit(bullet['img'], (int(bullet['x']), int(bullet['y'])))
                else:
                    self.screen.blit(bullet['img'], (int(bullet['x']), int(bullet['y'])))
        pygame.display.flip()

    def is_done(self):
        return self.state == 'done'

# --- Attack4: Sword Tunnel ---
class SwordTunnelSword:
    def __init__(self, x, y, direction, speed, up_img, down_img, up_img_red, down_img_red, heart_rect, trail_length=6, trail_alphas=None):
        self.x = x
        self.y = y
        self.direction = direction
        self.speed = speed
        self.up_img = up_img
        self.down_img = down_img
        self.up_img_red = up_img_red
        self.down_img_red = down_img_red
        self.heart_rect = heart_rect
        self.trail = []
        self.trail_length = trail_length
        self.trail_alphas = trail_alphas or [120, 90, 60, 40, 25, 10]
        self.red = False
        self.angle = 0
        self._red_state = False  # Track if currently red
        self._red_triggered = False  # Track if red was triggered

    def update(self, dt, heart_rect, final_phase=False, heart_center=None):
        self.x -= self.speed * dt / 16.67

        self.trail.insert(0, (self.x, self.y))
        if len(self.trail) > self.trail_length:
            self.trail.pop()

        sword_rect = self.get_rect()
        heart_center_x = heart_rect.centerx
        sword_center_x = sword_rect.centerx
        # Red logic: turn red when 20px to the right, stay red until 10px to the left
        if not self._red_state:
            if sword_center_x < heart_center_x + 10:
                self._red_state = True
        else:
            if sword_center_x < heart_center_x - 10:
                self._red_state = False
        self.red = self._red_state

    def get_rect(self):
        img = self.up_img
        rect = img.get_rect()
        rect.center = (int(self.x), int(self.y))
        return rect

    def draw(self, screen):
        img = self.up_img if self.direction == 'up' else self.down_img
        img_red = self.up_img_red if self.direction == 'up' else self.down_img_red
        for i, (tx, ty) in enumerate(reversed(self.trail)):
            timg = img_red if self.red else img
            timg = pygame.transform.rotate(timg, self.angle)
            timg = timg.copy()
            timg.set_alpha(self.trail_alphas[i])
            rect = timg.get_rect()
            rect.center = (int(tx), int(ty))
            screen.blit(timg, rect)
        main_img = img_red if self.red else img
        main_img = pygame.transform.rotate(main_img, self.angle)
        rect = main_img.get_rect()
        rect.center = (int(self.x), int(self.y))
        screen.blit(main_img, rect)


class Attack4:
    def __init__(self, screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
                 kris_idle_frames, kris_frame_idx, kris_rect,
                 susie_idle_frames, susie_frame_idx, susie_rect,
                 ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
                 battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
                 heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
                 knight_idle_img, show_knight_idle, clock,
                 base_dir=None, player_speed=2):
        self.screen = screen
        self.bg_img = bg_img
        self.fountain_scaled_frames = fountain_scaled_frames
        self.fountain_frame_idx = fountain_frame_idx
        self.kris_idle_frames = kris_idle_frames
        self.kris_frame_idx = kris_frame_idx
        self.kris_rect = kris_rect
        self.susie_idle_frames = susie_idle_frames
        self.susie_frame_idx = susie_frame_idx
        self.susie_rect = susie_rect
        self.ralsei_idle_frames = ralsei_idle_frames
        self.ralsei_frame_idx = ralsei_frame_idx
        self.ralsei_rect = ralsei_rect
        self.battle_box_rect = battle_box_rect.copy()
        self.battle_box_color = battle_box_color
        self.battle_box_border_color = battle_box_border_color
        self.battle_box_border = battle_box_border
        self.heart_img_0 = heart_img_0
        self.heart_img_1 = heart_img_1
        self.player_x = player_x
        self.player_y = player_y
        self.heart_size = heart_size
        self.font = font
        self.player_lives = player_lives
        self.invincible = invincible
        self.invincible_until = 0
        self.knight_idle_img = knight_idle_img
        self.show_knight_idle = show_knight_idle
        self.clock = clock
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.player_speed = player_speed
        self.swords = []
        self.sword_pairs = 60
        self.attack_duration = 10000  # ms
        self.spawn_interval = self.attack_duration / self.sword_pairs
        self.last_spawn_time = 0
        self.start_time = 0
        self.trail_length = 6
        self.trail_alphas = [120, 90, 60, 40, 25, 10]
        self.final_phase = False
        self.final_phase_triggered = False
        self.sword_spawn_count = 0
        self.last_offset = 0
        self.current_offset = 0.0
        self.offset_velocity = 1.0  
        self.offset_range = 10  
        self.wave_time = 0.0  # increments over time
        self.wave_speed = 0.75  # lower = slower wave
        self.wave_amplitude = 6.0  # reduced amplitude for smoother wave
        self.load_assets()
        # Replace wave pattern with explicit offset sequence
        self.wave_offsets = [
            1,   # down
            -1, -2,  # up twice
            2, 1,    # down twice
            -1, -2,  # up twice
            0        # back to center
        ]
        self.wave_offset_idx = 0
        self.wave_offset_unit = 0.5  # multiplier for heart_size
        # Explicit wave states: (offset, count)
        # Dramatic wave: larger offsets and amplitude
        self.wave_states = [
            (0, 4),    # down for 8 swords
            (-4, 6),   # up for 6 swords
            (0, 4),   # up higher for 6 swords
            (4, 6),    # down lower for 8 swords
            (0, 4),    # straight for 4 swords
            (-4, 6),    # down lower for 8 swords
            (0, 4),   # up higher for 6 swords
            (4, 6),    # straight for 4 swords
            (0, 4),   # down for 8 swords
            (-4, 6),   # up for 6 swords
            (0, 4),    # up higher for 6 swords
            (4, 6),    # down lower for 8 swords
            (0, 4)     # straight for 4 swords
        ]
        self.wave_state_idx = 0
        self.wave_state_count = 0
        self.wave_offset_unit = 1.5  # much larger amplitude

    def load_assets(self):
        # Load sword sprites and scale them 3x
        tunnel_dir = os.path.join(self.base_dir, 'sprites', 'spr_knight_sword_tunnel')
        up_img = pygame.image.load(os.path.join(tunnel_dir, 'spr_knight_longsword_up.png')).convert_alpha()
        down_img = pygame.image.load(os.path.join(tunnel_dir, 'spr_knight_longsword_down.png')).convert_alpha()
        up_img_red = pygame.image.load(os.path.join(tunnel_dir, 'spr_knight_longsword_up_red.png')).convert_alpha()
        down_img_red = pygame.image.load(os.path.join(tunnel_dir, 'spr_knight_longsword_down_red.png')).convert_alpha()
        scale = 1.5
        self.up_img = pygame.transform.smoothscale(up_img, (up_img.get_width()*scale, up_img.get_height()*scale))
        self.down_img = pygame.transform.smoothscale(down_img, (down_img.get_width()*scale, down_img.get_height()*scale))
        self.up_img_red = pygame.transform.smoothscale(up_img_red, (up_img_red.get_width()*scale, up_img_red.get_height()*scale))
        self.down_img_red = pygame.transform.smoothscale(down_img_red, (down_img_red.get_width()*scale, down_img_red.get_height()*scale))

    def run(self):
        running = True
        self.start_time = pygame.time.get_ticks()
        self.last_spawn_time = self.start_time
        dt = 16
        timeout_duration = 15000  # 15 seconds timeout
        # Animation timers for idle anims
        self.fountain_anim_timer = getattr(self, 'fountain_anim_timer', 0)
        self.kris_anim_timer = getattr(self, 'kris_anim_timer', 0)
        self.susie_anim_timer = getattr(self, 'susie_anim_timer', 0)
        self.ralsei_anim_timer = getattr(self, 'ralsei_anim_timer', 0)
        while running:
            # --- Advance animation timers and frame indices ---
            self.fountain_anim_timer += 1
            if self.fountain_anim_timer >= 16:
                self.fountain_frame_idx = (self.fountain_frame_idx + 1) % len(self.fountain_scaled_frames)
                self.fountain_anim_timer = 0
            self.kris_anim_timer += 1
            if self.kris_anim_timer >= 8:
                self.kris_frame_idx = (self.kris_frame_idx + 1) % len(self.kris_idle_frames)
                self.kris_anim_timer = 0
            self.susie_anim_timer += 1
            if self.susie_anim_timer >= 8:
                self.susie_frame_idx = (self.susie_frame_idx + 1) % len(self.susie_idle_frames)
                self.susie_anim_timer = 0
            self.ralsei_anim_timer += 1
            if self.ralsei_anim_timer >= 8:
                self.ralsei_frame_idx = (self.ralsei_frame_idx + 1) % len(self.ralsei_idle_frames)
                self.ralsei_anim_timer = 0
            now = pygame.time.get_ticks()
            elapsed = now - self.start_time
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit()
            # Player movement
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                self.player_x -= self.player_speed
            if keys[pygame.K_RIGHT]:
                self.player_x += self.player_speed
            if keys[pygame.K_UP]:
                self.player_y -= self.player_speed
            if keys[pygame.K_DOWN]:
                self.player_y += self.player_speed
            # Clamp player to battle box
            playable_rect = self.battle_box_rect.inflate(-2 * self.battle_box_border, -2 * self.battle_box_border)
            self.player_x = max(playable_rect.left, min(self.player_x, playable_rect.right - self.heart_size))
            self.player_y = max(playable_rect.top, min(self.player_y, playable_rect.bottom - self.heart_size))
            # Spawn swords
            if elapsed < self.attack_duration and self.sword_spawn_count < self.sword_pairs:
                if now - self.last_spawn_time >= self.spawn_interval:
                    # Apply wave offset smoothly
                    self.wave_time += 0.5  # slower wave movement
                    offset_raw = math.sin(self.wave_time * 0.2)
                    self.current_offset = offset_raw * self.wave_amplitude
                    heart_offset = int(self.current_offset * (self.heart_size / 2))  # Larger offset multiplier

                    # Set up sword positions with the wave offset
                    gap = 2 * self.heart_size  # Proper gap for dodgeability
                    # Center the sword pair in the battle box
                    base_center_y = self.battle_box_rect.centery
                    # Position the UP sword above center
                    # Get half-height of sword images
                    up_half = self.up_img.get_height() // 2
                    down_half = self.down_img.get_height() // 2

                    # Center the swords around the gap using .center alignment
                    up_y = base_center_y - gap // 2 - up_half + heart_offset
                    down_y = base_center_y + gap // 2 + down_half + heart_offset


                    # Only clamp if the pair would go completely out of bounds
                    # If down sword would go above the box, shift both down
                    if down_y < self.battle_box_rect.top:
                        shift = self.battle_box_rect.top - down_y
                        down_y += shift
                        up_y += shift
                    # If up sword would go below the box, shift both up  
                    if up_y + self.up_img.get_height() > self.battle_box_rect.bottom:
                        shift = (up_y + self.up_img.get_height()) - self.battle_box_rect.bottom
                        up_y -= shift
                        down_y -= shift

                    x = self.battle_box_rect.right + 30
                    speed = 16
                    heart_rect = pygame.Rect(self.player_x, self.player_y, self.heart_size, self.heart_size)

                    up_sword = SwordTunnelSword(x, down_y, 'up', speed, self.up_img, self.down_img,
                                                self.up_img_red, self.down_img_red, heart_rect,
                                                self.trail_length, self.trail_alphas)

                    down_sword = SwordTunnelSword(x, up_y, 'down', speed, self.up_img, self.down_img,
                                                  self.up_img_red, self.down_img_red, heart_rect,
                                                  self.trail_length, self.trail_alphas)

                    self.swords.append(up_sword)
                    self.swords.append(down_sword)
                    self.last_spawn_time = now
                    self.sword_spawn_count += 1

            # Update swords
            heart_rect = pygame.Rect(self.player_x, self.player_y, self.heart_size, self.heart_size)
            heart_center = (self.player_x + self.heart_size // 2, self.player_y + self.heart_size // 2)
            for sword in self.swords:
                sword.update(dt, heart_rect, self.final_phase, heart_center)
            # Remove swords that have left the screen
            self.swords = [
                s for s in self.swords
                    if -200 < s.x < self.screen.get_width() + 200 and -200 < s.y < self.screen.get_height() + 200
            ]

            # Invincibility logic
            now2 = pygame.time.get_ticks()
            if now2 < self.invincible_until:
                self.invincible = True
            else:
                self.invincible = False
            # Collision detection
            hit_this_frame = False
            for sword in self.swords:
                sword_rect = sword.get_rect()
                # Create hitbox that's 85% of the sprite size
                hitbox_width = int(sword_rect.width * 0.85)
                hitbox_height = int(sword_rect.height * 0.85)
                hitbox_x = sword_rect.centerx - hitbox_width // 2
                hitbox_y = sword_rect.centery - hitbox_height // 2
                hitbox = pygame.Rect(hitbox_x, hitbox_y, hitbox_width, hitbox_height)
                heart_rect = pygame.Rect(self.player_x, self.player_y, self.heart_size, self.heart_size)
                if hitbox.colliderect(heart_rect):
                    if now2 > self.invincible_until:
                        self.player_lives = max(0, self.player_lives - 1)
                        self.invincible_until = now2 + 1000
                        self.invincible = True
            # Draw everything
            draw_main_scene(
                self.screen, self.bg_img, self.fountain_scaled_frames, self.fountain_frame_idx,
                self.kris_idle_frames, self.kris_frame_idx, self.kris_rect,
                self.susie_idle_frames, self.susie_frame_idx, self.susie_rect,
                self.ralsei_idle_frames, self.ralsei_frame_idx, self.ralsei_rect,
                self.battle_box_rect, self.battle_box_color, self.battle_box_border_color, self.battle_box_border,
                self.heart_img_0, self.heart_img_1, self.player_x, self.player_y, self.heart_size, self.font, self.player_lives, self.invincible,
                self.knight_idle_img, self.show_knight_idle, self.clock
            )
            # Draw swords
            for sword in self.swords:
                sword.draw(self.screen)
            
            # End the wave when all swords are gone after spawning ends
            if self.sword_spawn_count >= self.sword_pairs and not self.swords:
                    running = False

            # Timeout fallback to prevent infinite loops
            if elapsed > timeout_duration:
                running = False
                
            pygame.display.flip()
            dt = self.clock.tick(60)

# --- Attack5: Spinning Slash ---
class Attack5:
    def __init__(self, screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
                 kris_idle_frames, kris_frame_idx, kris_rect,
                 susie_idle_frames, susie_frame_idx, susie_rect,
                 ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
                 battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
                 heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
                 knight_idle_img, show_knight_idle, clock,
                 base_dir=None, player_speed=2, sequences=None):
        self.screen = screen
        self.bg_img = bg_img
        self.fountain_scaled_frames = fountain_scaled_frames
        self.fountain_frame_idx = fountain_frame_idx
        self.kris_idle_frames = kris_idle_frames
        self.kris_frame_idx = kris_frame_idx
        self.kris_rect = kris_rect
        self.susie_idle_frames = susie_idle_frames
        self.susie_frame_idx = susie_frame_idx
        self.susie_rect = susie_rect
        self.ralsei_idle_frames = ralsei_idle_frames
        self.ralsei_frame_idx = ralsei_frame_idx
        self.ralsei_rect = ralsei_rect
        self.battle_box_rect = battle_box_rect.copy()
        self.battle_box_color = battle_box_color
        self.battle_box_border_color = battle_box_border_color
        self.battle_box_border = battle_box_border
        self.heart_img_0 = heart_img_0
        self.heart_img_1 = heart_img_1
        self.player_x = player_x
        self.player_y = player_y
        self.heart_size = heart_size
        self.font = font
        self.player_lives = player_lives
        self.invincible = invincible
        self.invincible_until = 0
        self.knight_idle_img = knight_idle_img
        self.show_knight_idle = show_knight_idle
        self.clock = clock
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.player_speed = player_speed
        
        # Attack state
        self.state = 'knight_anim'
        self.state_timer = 0
        self.current_sequence = 0
        self.sequences = sequences or [
            ('spr_rk_spinslash1_red.png', 'spr_rk_spinslash1.png'),
            ('spr_rk_spinslash2_red.png', 'spr_rk_spinslash2.png'),
            ('spr_rk_spinslash2_red.png', 'spr_rk_spinslash2.png'),
            ('spr_rk_spinslash3_red.png', 'spr_rk_spinslash3.png'),
            ('spr_rk_spinslash4_red.png', 'spr_rk_spinslash4.png')
        ]
        
        # Knight animation
        self.knight_frame_idx = 0
        self.knight_anim_speed = 1000 // 6  # 6 frames over 1 second
        
        # Slash state
        self.slash_angle = 0
        self.slash_spin_speed = 400  # degrees per second (reduced from 720)
        self.slash_active = False
        self.slash_warning_active = False
        self.slash_warning_timer = 0
        self.slash_warning_duration = 100  # ms warning phase
        self.slash_damage_active = False
        self.slash_damage_timer = 0
        self.slash_damage_duration = 300  # ms (increased from 100ms)
        self.slash_spin_slowdown_timer = 0
        self.slash_spin_slowdown_duration = 1000  # ms to slow down (increased from 500ms)
        self.slash_position = None  # Store random position for non-centered slashes
        
        # Load assets
        self.load_assets()
        
        # Load sound effect
        try:
            self.spinslash_sfx = pygame.mixer.Sound(os.path.join(self.base_dir, 'sprites', 'sound_effects', 'spinslash.wav'))
        except:
            self.spinslash_sfx = None
        
        # Trail setup
        self.trail_length = 10
        self.trail_alphas = [255 // (i + 2) for i in range(self.trail_length)]
        self.knight_trail = []


    def load_assets(self):
        # Load knight attack animation frames
        knight_attack_dir = os.path.join(self.base_dir, 'sprites', 'spr_roaringknight_attack_ol_center')
        idle_size = self.knight_idle_img.get_size()
        self.knight_attack_frames = []
        for i in range(6):
            frame = pygame.image.load(os.path.join(knight_attack_dir, f'spr_roaringknight_attack_ol_center_{i}.png')).convert_alpha()
            self.knight_attack_frames.append(pygame.transform.smoothscale(frame, idle_size))
        
        # Load slash sprites
        slash_dir = os.path.join(self.base_dir, 'sprites', 'spr_rk_spinslash')
        self.slash_sprites = {}
        for red_sprite, white_sprite in self.sequences:
            try:
                red_img = pygame.image.load(os.path.join(slash_dir, red_sprite)).convert_alpha()
                white_img = pygame.image.load(os.path.join(slash_dir, white_sprite)).convert_alpha()
                self.slash_sprites[red_sprite] = (red_img, white_img)
            except pygame.error as e:
                print(f"Error: {e}")
                # Create a fallback sprite if loading fails
                fallback = pygame.Surface((64, 64), pygame.SRCALPHA)
                fallback.fill((255, 0, 0, 128))  # Red semi-transparent
                self.slash_sprites[red_sprite] = (fallback, fallback)
    
    def handle_player_movement(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.player_x -= self.player_speed
        if keys[pygame.K_RIGHT]:
            self.player_x += self.player_speed
        if keys[pygame.K_UP]:
            self.player_y -= self.player_speed
        if keys[pygame.K_DOWN]:
            self.player_y += self.player_speed
        
        # Clamp to battle box
        playable_rect = self.battle_box_rect.inflate(-2 * self.battle_box_border, -2 * self.battle_box_border)
        self.player_x = max(playable_rect.left, min(self.player_x, playable_rect.right - self.heart_size))
        self.player_y = max(playable_rect.top, min(self.player_y, playable_rect.bottom - self.heart_size))
    
    def update(self, dt):
        self.state_timer += dt
        self.handle_player_movement()
        
        # Update knight animation
        self.knight_frame_idx = min(self.state_timer // self.knight_anim_speed, len(self.knight_attack_frames) - 1)
        
        # Check if we should start a new sequence
        if self.state == 'knight_anim' and self.knight_frame_idx >= 1 and not self.slash_active:
            self.start_slash_sequence()
        
        # Update slash
        if self.slash_active:
            # Phase transitions - check these FIRST before updating timers
            if not self.slash_warning_active and not self.slash_damage_active:
                # Check if knight reached frame 3 (index 3) to start warning phase
                if self.knight_frame_idx >= 3:
                    self.activate_slash_warning()
            
            elif self.slash_warning_active:
                # Update warning phase timer
                self.slash_warning_timer += dt
                if self.slash_warning_timer >= self.slash_warning_duration:
                    self.activate_slash_damage()
            
            elif self.slash_damage_active:
                # Update damage phase timer
                self.slash_damage_timer += dt
                if self.slash_damage_timer >= self.slash_damage_duration:
                    self.end_slash_sequence()
            
            # Determine spin speed based on current phase
            if self.slash_warning_active:
                # Very slow spin during warning
                current_speed = 30
            elif self.slash_damage_active:
                # Stop spinning during damage phase
                current_speed = 0
            else:
                # Normal spinning with slowdown
                if self.knight_frame_idx >= 2:  # Start slowing down when knight reaches frame 2
                    self.slash_spin_slowdown_timer += dt
                    slowdown_progress = min(self.slash_spin_slowdown_timer / self.slash_spin_slowdown_duration, 1.0)
                    current_speed = 400 - (slowdown_progress * 370)  # Slow from 400 to 30 degrees/sec
                else:
                    current_speed = self.slash_spin_speed
            
            # Apply spin
            self.slash_angle += current_speed * dt / 1000.0
            self.slash_angle %= 360
        
        # Check collision during damage phase
        if self.slash_damage_active:
            self.check_collision()
        
        # Check if knight animation is complete and we need to reset for next sequence
        if self.state == 'knight_anim' and self.knight_frame_idx >= len(self.knight_attack_frames) - 1:
            if not self.slash_active:  # If no slash is active, we're done with this sequence
                self.end_slash_sequence()
    
    def start_slash_sequence(self):
        self.slash_active = True
        self.slash_warning_active = False
        self.slash_warning_timer = 0
        self.slash_damage_active = False
        self.slash_damage_timer = 0
        self.slash_spin_slowdown_timer = 0
        self.slash_angle = 0
        
        # Generate random position for non-centered slashes (starting from second slash)
        if self.current_sequence > 0:
            margin = 50  # pixels from edge
            min_x = self.battle_box_rect.left + margin
            max_x = self.battle_box_rect.right - margin
            min_y = self.battle_box_rect.top + margin
            max_y = self.battle_box_rect.bottom - margin
            
            random_x = random.randint(min_x, max_x)
            random_y = random.randint(min_y, max_y)
            self.slash_position = (random_x, random_y)
        else:
            # First slash uses center position
            self.slash_position = self.battle_box_rect.center
    
    def activate_slash_warning(self):
        self.slash_warning_active = True
        self.slash_warning_timer = 0
        # Play warning sound
        if self.spinslash_sfx:
            self.spinslash_sfx.play()
    
    def activate_slash_damage(self):
        self.slash_warning_active = False  # Exit warning phase
        self.slash_damage_active = True
        self.slash_damage_timer = 0
    
    def end_slash_sequence(self):
        self.slash_active = False
        self.slash_warning_active = False
        self.slash_damage_active = False
        self.slash_warning_timer = 0
        self.slash_damage_timer = 0
        self.slash_spin_slowdown_timer = 0
        self.current_sequence += 1
        
        if self.current_sequence >= len(self.sequences):
            self.state = 'done'
        else:
            # Reset for next sequence
            self.state_timer = 0
            self.knight_frame_idx = 0
    
    def check_collision(self):
        now = pygame.time.get_ticks()
        if now <= self.invincible_until:
            return
        
        # Get current slash sprite
        red_sprite, white_sprite = self.sequences[self.current_sequence]
        slash_img = self.slash_sprites[red_sprite][1]  # Use white sprite during damage phase
        
        # Create a surface to check collision
        # Scale slash to 300% of battle box size and rotate it
        scale_factor = 3
        scaled_width = int(self.battle_box_rect.width * scale_factor)
        scaled_height = int(self.battle_box_rect.height * scale_factor)
        scaled_slash = pygame.transform.smoothscale(slash_img, (scaled_width, scaled_height))
        rotated_slash = pygame.transform.rotate(scaled_slash, self.slash_angle)
        
        # Get player position
        player_rect = pygame.Rect(self.player_x, self.player_y, self.heart_size, self.heart_size)
        player_center = (self.player_x + self.heart_size // 2, self.player_y + self.heart_size // 2)
        
        # Calculate where the rotated slash is positioned (same as in draw method)
        slash_rect = rotated_slash.get_rect()
        slash_rect.center = self.slash_position
        
        # Check if player rectangle overlaps with the slash rectangle
        if player_rect.colliderect(slash_rect):
            # Additional check: sample multiple points in the player area
            hit_detected = False
            sample_points = [
                (player_center[0], player_center[1]),  # Center
                (player_rect.left + 5, player_rect.top + 5),  # Top-left
                (player_rect.right - 5, player_rect.top + 5),  # Top-right
                (player_rect.left + 5, player_rect.bottom - 5),  # Bottom-left
                (player_rect.right - 5, player_rect.bottom - 5)  # Bottom-right
            ]
            
            for px, py in sample_points:
                # Convert to slash-relative coordinates
                rel_x = px - slash_rect.left
                rel_y = py - slash_rect.top
                
                if (0 <= rel_x < rotated_slash.get_width() and 
                    0 <= rel_y < rotated_slash.get_height()):
                    try:
                        pixel_alpha = rotated_slash.get_at((int(rel_x), int(rel_y)))[3]
                        if pixel_alpha > 100:  # Only hit if pixel has significant alpha (actual slash line)
                            hit_detected = True
                            break
                    except (IndexError, ValueError):
                        continue
            
            if hit_detected:
                self.player_lives = max(0, self.player_lives - 1)
                self.invincible_until = now + 1000  # 1 second invincibility
                self.invincible = True  
    def draw(self):
        # Draw main scene
        draw_main_scene(
            self.screen, self.bg_img, self.fountain_scaled_frames, self.fountain_frame_idx,
            self.kris_idle_frames, self.kris_frame_idx, self.kris_rect,
            self.susie_idle_frames, self.susie_frame_idx, self.susie_rect,
            self.ralsei_idle_frames, self.ralsei_frame_idx, self.ralsei_rect,
            self.battle_box_rect, self.battle_box_color, self.battle_box_border_color, self.battle_box_border,
            self.heart_img_0, self.heart_img_1, self.player_x, self.player_y, self.heart_size, self.font, self.player_lives, self.invincible,
            None, False, self.clock
        )
        # Draw knight attack animation
        if self.state != 'done':
            knight_img = self.knight_attack_frames[self.knight_frame_idx]
            knight_rect = knight_img.get_rect()
            knight_rect.left = self.battle_box_rect.right + 40
            knight_rect.centery = self.kris_rect.centery + 20
            # --- Knight sprite trail logic ---
            self.knight_trail.insert(0, (knight_img.copy(), knight_rect.copy()))
            if len(self.knight_trail) > self.trail_length:
                self.knight_trail.pop()

            for i, (img, rect) in enumerate(reversed(self.knight_trail)):
                if i < len(self.trail_alphas):
                    # Create a separate copy for alpha modification
                    trail_img = img.copy()
                    trail_img.set_alpha(self.trail_alphas[i])
                    # Draw with a slight offset to simulate motion blur
                    offset_rect = rect.copy()
                    offset_rect.left -= i * 2  # Adjust offset as needed
                    self.screen.blit(trail_img, offset_rect)

            # Draw the main knight sprite
            self.screen.blit(knight_img, knight_rect)

        # Draw slash if active
        if self.slash_active and self.current_sequence < len(self.sequences):
            red_sprite, white_sprite = self.sequences[self.current_sequence]
            red_img, white_img = self.slash_sprites[red_sprite]
            
            # Use white sprite during damage phase, red sprite during warning and spinning phases
            slash_img = white_img if self.slash_damage_active else red_img
            
            # Scale to 300% of battle box size (larger for more dodgeable gaps when clipped)
            scale_factor = 3
            scaled_width = int(self.battle_box_rect.width * scale_factor)
            scaled_height = int(self.battle_box_rect.height * scale_factor)
            scaled_slash = pygame.transform.smoothscale(slash_img, (scaled_width, scaled_height))
            
            # Rotate the slash
            rotated_slash = pygame.transform.rotate(scaled_slash, self.slash_angle)
            
            # Position the rotated slash
            slash_rect = rotated_slash.get_rect()
            slash_rect.center = self.slash_position
            
            # Create a clipping area for the battle box
            clip_rect = self.screen.get_clip()
            self.screen.set_clip(self.battle_box_rect)
            
            # Draw the slash
            self.screen.blit(rotated_slash, slash_rect)
            
            # Restore clipping
            self.screen.set_clip(clip_rect)
        
        pygame.display.flip()
    
    def run(self):
        running = True
        while not self.is_done() and running:
            dt = self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit()
            
            self.update(dt)
            self.draw()
    
    def is_done(self):
        return self.state == 'done'

# --- Attack7: Random Cut Attack (based on Attack3) ---
class Attack7:
    def __init__(self, screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
                 kris_idle_frames, kris_frame_idx, kris_rect,
                 susie_idle_frames, susie_frame_idx, susie_rect,
                 ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
                 battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
                 heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
                 knight_idle_img, show_knight_idle, clock,
                 knight_trail, trail_length, trail_alphas,
                 cycles=7, base_dir=None, player_speed=1):
        # Generate random cut modes for each cycle
        cut_modes = []
        for _ in range(cycles):
            cut_modes.append(random.choice(['vertical', 'horizontal']))
        
        # Create Attack3 instance with random cut modes
        self.attack3 = Attack3(
            screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
            kris_idle_frames, kris_frame_idx, kris_rect,
            susie_idle_frames, susie_frame_idx, susie_rect,
            ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
            battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
            knight_idle_img, show_knight_idle, clock,
            knight_trail, trail_length, trail_alphas,
            cut_mode='vertical', cycles=cycles, base_dir=base_dir, player_speed=player_speed, cut_modes=cut_modes
        )
    
    def run(self):
        self.attack3.run()
    
    def is_done(self):
        return self.attack3.is_done()

class Attack8(Attack2):
    def __init__(self, *args, **kwargs):
        kwargs['show_wheel'] = True
        super().__init__(*args, **kwargs)

# --- Attack10: Slash Wheel ---
class Attack10:
    def __init__(self, screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
                 kris_idle_frames, kris_frame_idx, kris_rect,
                 susie_idle_frames, susie_frame_idx, susie_rect,
                 ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
                 battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
                 heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
                 knight_idle_img, show_knight_idle, clock,
                 base_dir=None, player_speed=2):
        self.screen = screen
        self.bg_img = bg_img
        self.fountain_scaled_frames = fountain_scaled_frames
        self.fountain_frame_idx = fountain_frame_idx
        self.kris_idle_frames = kris_idle_frames
        self.kris_frame_idx = kris_frame_idx
        self.kris_rect = kris_rect
        self.susie_idle_frames = susie_idle_frames
        self.susie_frame_idx = susie_frame_idx
        self.susie_rect = susie_rect
        self.ralsei_idle_frames = ralsei_idle_frames
        self.ralsei_frame_idx = ralsei_frame_idx
        self.ralsei_rect = ralsei_rect
        self.battle_box_rect = battle_box_rect.copy()
        self.battle_box_color = battle_box_color
        self.battle_box_border_color = battle_box_border_color
        self.battle_box_border = battle_box_border
        self.heart_img_0 = heart_img_0
        self.heart_img_1 = heart_img_1
        self.player_x = player_x
        self.player_y = player_y
        self.heart_size = heart_size
        self.font = font
        self.player_lives = player_lives
        self.invincible = invincible
        self.invincible_until = 0
        self.knight_idle_img = knight_idle_img
        self.show_knight_idle = show_knight_idle
        self.clock = clock
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.prepare_sprite = pygame.image.load("sprites/spr_roaringknight_flurry/spr_roaringknight_flurry_prepare.png").convert_alpha() # full path because it didn't load otherwise for some reason
        self.player_speed = player_speed
        self.state = 'attack9'  # 'attack9' or 'slash_wheel'
        self.attack9 = None
        self.slash_wheel_done = False
        self.play_slashwheel_sfx_cycle = 0
        # --- Knight sprite trail (ghost afterimage) ---
        self.knight_trail = []
        self.trail_length = 10
        self.trail_alphas = [80, 70, 60, 50, 40, 30, 20, 15, 10, 5][:self.trail_length]
        self.load_assets()

    def load_assets(self):
        # Flurry animation
        flurry_dir = os.path.join(self.base_dir, 'sprites', 'spr_roaringknight_flurry')
        # Load and scale flurry frames to match knight idle size (3x)
        knight_idle_img = pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_roaringknight_idle.png')).convert_alpha()
        knight_target_size = (int(knight_idle_img.get_width() * 3), int(knight_idle_img.get_height() * 3))
        self.flurry_frames = [pygame.transform.smoothscale(
            pygame.image.load(os.path.join(flurry_dir, f'spr_roaringknight_flurry_{i}.png')).convert_alpha(),
            knight_target_size
        ) for i in range(3)]
        # Load prepare sprite
        self.prepare_sprite = pygame.transform.smoothscale(
            pygame.image.load(os.path.join(flurry_dir, 'spr_roaringknight_flurry_prepare.png')).convert_alpha(),
            knight_target_size
        )
        self.flurry_frame_idx = 0
        self.flurry_anim_timer = 0
        self.flurry_anim_speed = 4  # frames per sprite
        # Slash sprite
        spinslash_dir = os.path.join(self.base_dir, 'sprites', 'spr_rk_spinslash')
        self.spinslash_img = pygame.image.load(os.path.join(spinslash_dir, 'spr_rk_spinslash_red.png')).convert_alpha()
        # --- NEW: Load alt slash animation frames for marks ---
        slash_dir = os.path.join(self.base_dir, 'sprites', 'spr_roaringknight_slash_red_alt')
        self.slash_anim_frames = []
        for i in range(5, 10):
            frame_path = os.path.join(slash_dir, f'spr_roaringknight_slash_red_alt_{i}.png')
            if os.path.exists(frame_path):
                self.slash_anim_frames.append(pygame.image.load(frame_path).convert_alpha())
        self.slash_anim_frames_count = len(self.slash_anim_frames)
        self.slash_anim_advance_per_frame = 2  # 2 frames per game frame
        # For scaling
        self.box_side = self.battle_box_rect.width
        self.box_height = self.battle_box_rect.height
        # Slash wheel state
        self.slash_wheel_total_spins = 2  # 2 full turns
        self.slash_wheel_angle_step = 6   # 4 degrees per slash
        self.slash_wheel_current_angle = 0.0
        self.slash_wheel_slashes_done = 0
        self.slash_wheel_max_slashes = int(360 / self.slash_wheel_angle_step * self.slash_wheel_total_spins)
        self.slash_wheel_anim_frame = 0
        self.slash_wheel_animating = False
        self.slash_wheel_anim_angle = 0.0
        self.slash_wheel_anim_done = False
        self.slash_wheel_anim_start = False
        self.slashwheel_spin_stopped_angle = None
        self.slash_scale = int(self.box_side * 1.5)
        self.frame_counter = 0
        # Ensure spinslash sound effect is loaded
        self.spinslash_sfx = pygame.mixer.Sound(os.path.join(self.base_dir, 'sprites', 'sound_effects', 'spinslash.wav'))
        # Add slash state sequence for the slash wheel phase
        self.slashwheel_slash_states = ['0', '1', 'trail']
        # Initialize SFX played flag for slash wheel
        self.slashwheel_sfx_played = False
        # Load slash wheel sprites
        slashwheel_dir = os.path.join(self.base_dir, 'sprites', 'spr_rk_slashwheel')
        self.slashwheel_img_0 = pygame.image.load(os.path.join(slashwheel_dir, 'spr_rk_slashwheel_0.png')).convert_alpha()
        self.slashwheel_img_1 = pygame.image.load(os.path.join(slashwheel_dir, 'spr_rk_slashwheel_1.png')).convert_alpha()
        self.slashwheel_img_trail = pygame.image.load(os.path.join(slashwheel_dir, 'spr_rk_slashwheel_trail.png')).convert_alpha()
        # Set scale for slash wheel sprites
        self.slashwheel_scale_w = int(self.battle_box_rect.width * 2.82) # (multiplied by square root of 8, which is the length of the diagonal of the battle box)
        self.slashwheel_scale_h = max(8, int(self.battle_box_rect.width // 6))
        # For the trail: very thin, very tall
        self.slashwheel_trail_w = max(2, int(self.battle_box_rect.width // 50))
        self.slashwheel_trail_h = int(self.battle_box_rect.width * 2.82)

    def run(self):
        # Part 1: Attack9 logic (reuse Attack5)
        self.attack9 = Attack5(
            self.screen, self.bg_img, self.fountain_scaled_frames, self.fountain_frame_idx,
            self.kris_idle_frames, self.kris_frame_idx, self.kris_rect,
            self.susie_idle_frames, self.susie_frame_idx, self.susie_rect,
            self.ralsei_idle_frames, self.ralsei_frame_idx, self.ralsei_rect,
            self.battle_box_rect, self.battle_box_color, self.battle_box_border_color, self.battle_box_border,
            self.heart_img_0, self.heart_img_1, self.player_x, self.player_y, self.heart_size, self.font, self.player_lives, self.invincible,
            self.knight_idle_img, self.show_knight_idle, self.clock,
            base_dir=self.base_dir, player_speed=self.player_speed,
            sequences=[
                ('spr_rk_spinslash4_red.png', 'spr_rk_spinslash4.png'),
                ('spr_rk_spinslash4_red.png', 'spr_rk_spinslash4.png'),
                ('spr_rk_spinslash4_red.png', 'spr_rk_spinslash4.png'),
                ('spr_rk_spinslash4_red.png', 'spr_rk_spinslash4.png'),
                ('spr_rk_spinslash4_red.png', 'spr_rk_spinslash4.png')
            ]
        )
        self.attack9.run()
        self.player_lives = self.attack9.player_lives
        # Part 2: Slash Wheel
        self.state = 'slash_wheel'
        self.run_slash_wheel()

    def run_slash_wheel(self):
        # Wait for the spin to finish, then start the slash sequence
        running = True
        self.flurry_anim_timer = 0
        self.flurry_frame_idx = 0
        self.wheel_angle = 0.0
        self.spin_speed = 400
        self.wheel_angle_total = 0.0
        self.slashwheel_state = 'spin'
        self.slashwheel_spin_stopped_angle = None
        self.slashwheel_slashes = []
        self.slashwheel_trails = []
        self.slashwheel_current_index = 0
        self.slashwheel_slash_state_idx = 0
        self.slashwheel_slash_start_time = 0
        self.slashwheel_prev_slash = None
        self.slashwheel_prev_trail_time = 0
        spin_end_angle = 360 * 2
        frame_counter = 0
        self.slashwheel_slash_start_frame = frame_counter  # Initialize before loop
        self.last_slash_sound_played = (-1, -1)  # (slash_index, state_idx) for sound effect logic
        while running:
            dt = self.clock.tick(60)
            now = pygame.time.get_ticks()
            frame_counter += 1
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit()
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                self.player_x -= self.player_speed
            if keys[pygame.K_RIGHT]:
                self.player_x += self.player_speed
            if keys[pygame.K_UP]:
                self.player_y -= self.player_speed
            if keys[pygame.K_DOWN]:
                self.player_y += self.player_speed
            playable_rect = self.battle_box_rect.inflate(-2 * self.battle_box_border, -2 * self.battle_box_border)
            self.player_x = max(playable_rect.left, min(self.player_x, playable_rect.right - self.heart_size))
            self.player_y = max(playable_rect.top, min(self.player_y, playable_rect.bottom - self.heart_size))
            self.flurry_anim_timer += 1
            if self.flurry_anim_timer >= self.flurry_anim_speed:
                self.flurry_frame_idx = (self.flurry_frame_idx + 1) % len(self.flurry_frames)
                self.flurry_anim_timer = 0
            # --- Collision logic for slash wheel phase ---
            if self.slashwheel_state == 'slash':
                # Only check collision during the '1' (active) state
                if self.slashwheel_current_index < self.slash_wheel_max_slashes:
                    angle = (self.slashwheel_spin_stopped_angle + self.slashwheel_current_index * self.slash_wheel_angle_step) % 360
                    state = self.slashwheel_slash_states[self.slashwheel_slash_state_idx]
                    if state == '1':
                        # Get the slash image and transform it as in _draw_slashwheel_colored
                        img = self.slashwheel_img_1
                        scaled = pygame.transform.smoothscale(img, (self.slashwheel_scale_w, self.slashwheel_scale_h))
                        rotated = pygame.transform.rotate(scaled, angle)
                        rect = rotated.get_rect(center=self.battle_box_rect.center)
                        player_rect = pygame.Rect(self.player_x, self.player_y, self.heart_size, self.heart_size)
                        player_center = (self.player_x + self.heart_size // 2, self.player_y + self.heart_size // 2)
                        # Only check if player is not invincible
                        if now > getattr(self, 'invincible_until', 0):
                            if player_rect.colliderect(rect):
                                # Sample points in the player rect for pixel-perfect alpha check
                                hit_detected = False
                                sample_points = [
                                    (player_center[0], player_center[1]),
                                    (player_rect.left + 5, player_rect.top + 5),
                                    (player_rect.right - 5, player_rect.top + 5),
                                    (player_rect.left + 5, player_rect.bottom - 5),
                                    (player_rect.right - 5, player_rect.bottom - 5)
                                ]
                                for px, py in sample_points:
                                    rel_x = px - rect.left
                                    rel_y = py - rect.top
                                    if (0 <= rel_x < rotated.get_width() and 0 <= rel_y < rotated.get_height()):
                                        try:
                                            pixel_alpha = rotated.get_at((int(rel_x), int(rel_y)))[3]
                                            if pixel_alpha > 100:
                                                hit_detected = True
                                                break
                                        except (IndexError, ValueError):
                                            continue
                                if hit_detected:
                                    self.player_lives = max(0, self.player_lives - 1)
                                    self.invincible_until = now + 1000  # 1 second invincibility
                                    self.invincible = True
            if self.slashwheel_state == 'spin':
                self.wheel_angle_total += self.spin_speed * dt / 1000.0
                self.wheel_angle = self.wheel_angle_total % 360
                self.draw_slashwheel(now, spinning=True)
                if self.wheel_angle_total >= spin_end_angle:
                    self.slashwheel_state = 'slash'
                    self.slashwheel_spin_stopped_angle = self.wheel_angle % 360
                    self.slashwheel_slash_start_time = now
                    self.slashwheel_current_index = 0
                    self.slashwheel_slash_state_idx = 0
                    self.slashwheel_prev_slash = None
                    self.slashwheel_prev_trail_time = 0
            elif self.slashwheel_state == 'slash':
                # State machine for each slash
                if self.slashwheel_current_index >= self.slash_wheel_max_slashes and not self.slashwheel_trails:
                    self.slashwheel_state = 'done'
                    continue
                # Handle trail expiration
                self.slashwheel_trails = [(a, f) for (a, f) in self.slashwheel_trails if now - f < 1]
                # Handle new slash
                if self.slashwheel_current_index < self.slash_wheel_max_slashes:
                    angle = (self.slashwheel_spin_stopped_angle + self.slashwheel_current_index * self.slash_wheel_angle_step) % 360
                    state = self.slashwheel_slash_states[self.slashwheel_slash_state_idx]
                    if state == '0':
                        self.draw_slashwheel(now, spinning=False, slash_angle=angle, slash_state='0', prev_trail=self.slashwheel_prev_slash)
                        if self.slashwheel_slash_state_idx_timer(frame_counter):
                            self.slashwheel_slash_state_idx = 1
                            self.slashwheel_slash_start_frame = frame_counter
                    elif state == '1':
                        self.draw_slashwheel(now, spinning=False, slash_angle=angle, slash_state='1', prev_trail=self.slashwheel_prev_slash)
                        if self.slashwheel_slash_state_idx_timer(frame_counter):
                            self.slashwheel_slash_state_idx = 2
                            self.slashwheel_slash_start_frame = frame_counter
                    elif state == 'trail':
                        if self.slashwheel_prev_slash is not None:
                            self.slashwheel_trails.append((self.slashwheel_prev_slash, frame_counter))
                        self.draw_slashwheel(now, spinning=False, slash_angle=angle, slash_state='trail', prev_trail=None)
                        if self.slashwheel_slash_state_idx_timer(frame_counter):
                            self.slashwheel_current_index += 1
                            self.slashwheel_slash_state_idx = 0
                            self.slashwheel_slash_start_frame = frame_counter
                            self.slashwheel_prev_slash = angle
                            if self.play_slashwheel_sfx_cycle == 0:
                                self.spinslash_sfx.play()
                                self.play_slashwheel_sfx_cycle += 1
                            if self.play_slashwheel_sfx_cycle >= 3:
                                self.play_slashwheel_sfx_cycle = 0
                            else:
                                self.play_slashwheel_sfx_cycle += 1
                else:
                    self.draw_slashwheel(now, spinning=False, slash_angle=None, slash_state=None, prev_trail=None)
            elif self.slashwheel_state == 'done':
                running = False

    def slashwheel_slash_state_idx_timer(self, frame_counter):
        # Returns True if 1 frame has passed since last state change
        return frame_counter - getattr(self, 'slashwheel_slash_start_frame', 0) >= 1

    def draw_slashwheel(self, now, spinning=False, slash_angle=None, slash_state=None, prev_trail=None):
        draw_main_scene(
            self.screen, self.bg_img, self.fountain_scaled_frames, self.fountain_frame_idx,
            self.kris_idle_frames, self.kris_frame_idx, self.kris_rect,
            self.susie_idle_frames, self.susie_frame_idx, self.susie_rect,
            self.ralsei_idle_frames, self.ralsei_frame_idx, self.ralsei_rect,
            self.battle_box_rect, self.battle_box_color, self.battle_box_border_color, self.battle_box_border,
            self.heart_img_0, self.heart_img_1, self.player_x, self.player_y, self.heart_size, self.font, self.player_lives, pygame.time.get_ticks() < getattr(self, 'invincible_until', 0),
            None, False, self.clock
        )
        # Use prepare sprite during spinning phase, otherwise use flurry animation
        knight_img = self.prepare_sprite if spinning else self.flurry_frames[self.flurry_frame_idx]
        knight_rect = knight_img.get_rect()
        knight_rect.left = self.battle_box_rect.right + 40
        knight_rect.centery = self.kris_rect.centery + 20
        # --- Knight sprite trail logic ---
        self.knight_trail.insert(0, (knight_img.copy(), knight_rect.copy()))
        if len(self.knight_trail) > self.trail_length:
            self.knight_trail.pop()
        for i, (img, rect) in enumerate(reversed(self.knight_trail)):
            if i >= len(self.trail_alphas):
                break
            img = img.copy()
            img.set_alpha(self.trail_alphas[i])
            rect = rect.copy()
            rect.left += 40 + i * 10
            self.screen.blit(img, rect)
        # Draw the main knight sprite
        self.screen.blit(knight_img, knight_rect)
        # Draw spinning phase
        if spinning:
            orig_slash_w, orig_slash_h = self.spinslash_img.get_width(), self.spinslash_img.get_height()
            new_slash_w = int(self.battle_box_rect.width * 1.5)
            scale_factor = new_slash_w / orig_slash_w
            new_slash_h = int(orig_slash_h * scale_factor)
            scaled_slash = pygame.transform.smoothscale(self.spinslash_img, (new_slash_w, new_slash_h))
            rotated_slash = pygame.transform.rotate(scaled_slash, self.wheel_angle)
            slash_rect = rotated_slash.get_rect(center=self.battle_box_rect.center)
            prev_clip = self.screen.get_clip()
            self.screen.set_clip(self.battle_box_rect)
            self.screen.blit(rotated_slash, slash_rect)
            self.screen.set_clip(prev_clip)
            pygame.draw.rect(self.screen, self.battle_box_border_color, self.battle_box_rect, self.battle_box_border)
        else:
            # Draw all active trails
            for angle, f in self.slashwheel_trails:
                self._draw_slashwheel_trail(angle)
            # Draw current slash
            if slash_angle is not None and slash_state is not None:
                if slash_state == '0':
                    self._draw_slashwheel_colored(slash_angle, self.slashwheel_img_0)
                elif slash_state == '1':
                    self._draw_slashwheel_colored(slash_angle, self.slashwheel_img_1)
                elif slash_state == 'trail':
                    self._draw_slashwheel_trail(slash_angle)
        pygame.display.flip()

    def _draw_slashwheel_colored(self, angle, img):
        # Scale and rotate
        scaled = pygame.transform.smoothscale(img, (self.slashwheel_scale_w, self.slashwheel_scale_h))
        rotated = pygame.transform.rotate(scaled, angle)
        rect = rotated.get_rect(center=self.battle_box_rect.center)
        # Draw outside the box as normal
        self.screen.blit(rotated, rect)
        # Recolor inside the box using a temporary surface for the battle box
        box = self.battle_box_rect
        temp_surf = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
        temp_surf.blit(rotated, (-(box.left - rect.left), -(box.top - rect.top)))
        # Fast recolor using surfarray (only for non-transparent pixels)
        arr = pygame.surfarray.pixels3d(temp_surf)
        alpha = pygame.surfarray.pixels_alpha(temp_surf)
        arr[(alpha > 0)] = (252, 84, 92)
        del arr
        del alpha
        self.screen.blit(temp_surf, box.topleft)

    def _draw_slashwheel_trail(self, angle):
        # Scale and rotate the trail to be long and thin in the same direction as the main slashes
        scaled = pygame.transform.smoothscale(self.slashwheel_img_trail, (self.slashwheel_trail_h, self.slashwheel_trail_w))
        rotated = pygame.transform.rotate(scaled, angle)
        rect = rotated.get_rect(center=self.battle_box_rect.center)
        # Only draw inside the box using a temporary surface
        box = self.battle_box_rect
        temp_surf = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
        temp_surf.blit(rotated, (-(box.left - rect.left), -(box.top - rect.top)))
        self.screen.blit(temp_surf, box.topleft)

    def is_done(self):
        return self.state == 'done'


class FinalAttackSequence:
    def load_anim_frames(self, folder_name, numeric_sort=False):
        """
        Helper method to load animation frames from a folder.
        Args:
            folder_name: Name of the folder containing the frames
            numeric_sort: If True, sort files numerically instead of alphabetically
        Returns:
            List of loaded and converted animation frames
        """
        folder_path = os.path.join(self.base_dir, 'sprites', folder_name)
        files = [
            os.path.join(folder_path, f) for f in os.listdir(folder_path)
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]
        if numeric_sort:
            files.sort(key=lambda x: int(''.join(filter(str.isdigit, os.path.basename(x))) or 0))
        else:
            files = sorted(files)
        return [pygame.image.load(f).convert_alpha() for f in files]

    def __init__(self, screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
                 kris_idle_frames, kris_frame_idx, kris_rect,
                 susie_idle_frames, susie_frame_idx, susie_rect,
                 ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
                 battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
                 heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
                 knight_idle_img, show_knight_idle, clock,
                 base_dir=None, player_speed=2):
        self.base_dir = base_dir
        self.flourish_frames = self.load_anim_frames('spr_roaringknight_front_flourish', numeric_sort=True)
        self.flourish_animating = False
        self.flourish_start_time = 0
        self.flourish_duration = 1000  # 1 second
        self.roar_channel = None

        self.screen = screen
        self.bg_img = bg_img
        self.bg_img_initial = bg_img.copy()
        self.fountain_scaled_frames = fountain_scaled_frames
        self.fountain_frame_idx = fountain_frame_idx
        self.kris_idle_frames = kris_idle_frames
        self.kris_frame_idx = kris_frame_idx
        self.kris_rect = kris_rect
        self.susie_idle_frames = susie_idle_frames
        self.susie_frame_idx = susie_frame_idx
        self.susie_rect = susie_rect
        self.ralsei_idle_frames = ralsei_idle_frames
        self.ralsei_frame_idx = ralsei_frame_idx
        self.ralsei_rect = ralsei_rect
        self.battle_box_rect = battle_box_rect.copy()
        self.battle_box_color = battle_box_color
        self.battle_box_border_color = battle_box_border_color
        self.battle_box_border = battle_box_border
        self.heart_img_0 = heart_img_0
        self.heart_img_1 = heart_img_1
        self.player_x = player_x
        self.player_y = player_y
        self.heart_size = heart_size
        self.font = font
        self.player_lives = player_lives
        self.invincible = invincible
        self.knight_idle_img = knight_idle_img
        self.show_knight_idle = show_knight_idle
        self.clock = clock
        self.base_dir = base_dir
        self.player_speed = player_speed
        self.state = 0  # 0: expanding box, 1: knight aura, 2: phase 1, 3: phase 2, ...
        self.timer = 0
        self.box_expand_duration = 2000  # ms
        self.box_fade_duration = 2000  # ms
        self.box_expanded = False
        self.box_alpha = 255
        self.box_scale = 1.0
        self.box_target_scale = 2.0
        self.box_center = self.battle_box_rect.center
        self.screen_rect = self.screen.get_rect()
        # Load knight and glow sprites
        self.knight_img = pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_roaringknight_front_slash', 'spr_roaringknight_front_slash_0.png')).convert_alpha()
        self.knight_glow_img = pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_roaringknight_front_slash', 'spr_roaringknight_front_slash_glow.png')).convert_alpha()
        self.knight_pos = (self.screen_rect.centerx, self.screen_rect.centery - 100)
        self.knight_glow_layers = 3
        self.knight_glow_scales = [1.5, 2.0, 2.5]
        self.knight_glow_alphas = [100, 60, 30]
        self.phase1_started = False
        self.phase2_started = False
        # For later phases
        self.phase1_timer = 0
        self.phase2_timer = 0
        self.phase1_duration = 5000  # ms
        self.phase2_duration = 5000  # ms
        # Placeholder for stars
        self.stars = []
        self.spiral_stars = []
        # Phases 1+2 (star attack) setup
        self.star_img = pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_knight_bullet_star', 'spr_knight_bullet_star_0.png')).convert_alpha()
        self.last_star_spawn = 0
        self.star_spawn_interval = 250  # ms between spawns
        self.star_scale = 4.0  # 400%
        self.spiral_star_scale = 2.5 # 250%
        self.min_star_scale = 1.2  # Minimum scale for stars
        self.star_duration = 1200  # ms, faster star movement
        self.spiral_star_duration = 300  # ms, faster spiral stars
        self.phase1_duration = 4000  # ms
        self.phase2_duration = 4000  # ms
        self.phase1_timer = 0
        self.stars = []
        # Load star absorb sound effect
        self.absorb_sfx = pygame.mixer.Sound(os.path.join(self.base_dir, 'sprites', 'sound_effects', 'spr_knight_absorb_stars.wav'))
        self.absorb_sfx_played = False
        # Transition animation
        self.flourish_paused = False
        self.flourish_pause_start = 0
        self.flourish_pause_duration = 150  # ms, adjust as needed for the brief pause
        self.flourish_fadein_duration = 150  # ms, adjust as needed for fade-in
        self.flourish_fadein_start = 0
        self.flourish_fadein = False
        # Load flourish frames (do this once, not every frame)
        flourish_dir = os.path.join(self.base_dir, 'sprites', 'spr_roaringknight_front_flourish')
        flourish_files = sorted([os.path.join(flourish_dir, f) for f in os.listdir(flourish_dir) if f.endswith('.png')])
        scale_factor = 2.25

        # Use the original knight image as the reference for size
        orig_knight_img = pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_roaringknight_front_slash', 'spr_roaringknight_front_slash_0.png')).convert_alpha()
        target_size = (int(orig_knight_img.get_width() * scale_factor), int(orig_knight_img.get_height() * scale_factor))

        self.flourish_frames = [
            pygame.transform.smoothscale(pygame.image.load(f).convert_alpha(), target_size)
            for f in flourish_files
        ]
        self.flourish_frame_idx = 0
        self.flourish_anim_timer = 0
        self.flourish_anim_speed = 100  # ms per frame
        # Roar sequence 
        # After flourish frame setup
        roar_dir = os.path.join(self.base_dir, 'sprites', 'spr_roaringknight_front_roar')
        roar_files = sorted([os.path.join(roar_dir, f) for f in os.listdir(roar_dir) if f.endswith('.png')])
        self.roar_frames = [pygame.transform.smoothscale(pygame.image.load(f).convert_alpha(), target_size) for f in roar_files]
        self.roar_anim_speed = 200  # ms per frame
        self.roar_sfx = pygame.mixer.Sound(os.path.join(self.base_dir, 'sprites', 'sound_effects', 'spr_knight_roar.wav'))
        self.roar_sfx_played = False
        self.roar_duration = 4500  # ms, 4.5 seconds
        self.roar_star_spawn_interval = 250  # ms between spawns, doubled for longer delay
        self.last_roar_star_spawn = 0
        self.roar_stars = []
        # Load star animation frames
        star_anim_dir = os.path.join(self.base_dir, 'sprites', 'spr_knight_bullet_star')
        self.star_transform_frames = []
        for i in range(4):  # 4 frames in the animation
            frame = pygame.image.load(os.path.join(star_anim_dir, f'spr_knight_bullet_star_{i}.png')).convert_alpha()
            self.star_transform_frames.append(frame)
            
        # Load starchild sprites
        starchild_dir = os.path.join(self.base_dir, 'sprites', 'spr_knight_starchild')
        self.starchild_up = pygame.image.load(os.path.join(starchild_dir, 'spr_knight_starchild_up.png')).convert_alpha()
        self.starchild_down = pygame.image.load(os.path.join(starchild_dir, 'spr_knight_starchild_down.png')).convert_alpha()
        
        self.roar_star_img = self.star_img
        self.roar_star_min_scale = self.min_star_scale * 0.25  # 25% of the original size
        self.roar_star_max_scale = self.star_scale * 0.65  # 85% of the original size
        self.roar_star_duration = 2000 # ms, stars move slower to stay on screen
        # Acceleration variables for final phase
        self.roar_phase_start_time = 0
        self.roar_base_spawn_interval = 250
        self.roar_base_duration = 2000
        self.roar_acceleration_factor = 0.98  # Each star gets 2% faster spawn and movement (less aggressive)
        # Reverse flourish variables
        self.reverse_flourish_started = False
        self.reverse_flourish_start_time = 0
        self.reverse_flourish_delay = 500  # 0.5 seconds after roar ends
        self.reverse_flourish_frames = None
        # Star return state
        self.stars_returning = False
        # Final animation variables
        self.screen_height = self.screen.get_height()
        self.screen_width = self.screen.get_width()
        self.state6_start_time = None
        self.explosion_time_recorded = False
        self.diagonal_slash_img = pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_front_slash.png')).convert_alpha()
        self.front_slash_knight_frames = [ 
            pygame.image.load(f"sprites/spr_roaringknight_front_slash/spr_roaringknight_front_slash_{i}.png").convert_alpha() 
            for i in range(6) 
            ]
        self.knight_trail_img = pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_roaringknight_front_slash', 'spr_roaringknight_front_slash_5.png')).convert_alpha() # final frame of the slash animation
        # Load raw
        self.diagonal_slash_img_raw = pygame.image.load(os.path.join(self.base_dir, 'sprites', 'spr_front_slash.png')).convert_alpha()
        # Scale it
        self.target_height = self.screen_height * 2
        self.scale_factor = self.target_height / self.diagonal_slash_img_raw.get_height()
        self.target_width = int(self.diagonal_slash_img_raw.get_width() * self.scale_factor)
        self.diagonal_slash_img = pygame.transform.smoothscale(self.diagonal_slash_img_raw, (self.target_width, self.target_height))
        self.slash_duration = 500 # ms
        front_slash_dir = os.path.join(self.base_dir, 'sprites', 'spr_roaringknight_front_slash')
        front_slash_files = sorted([os.path.join(front_slash_dir, f) for f in os.listdir(front_slash_dir) if f.endswith('.png')])
        
        self.front_slash_frames = [
            pygame.transform.smoothscale(pygame.image.load(f).convert_alpha(), target_size)
            for f in front_slash_files
        ]
        self.front_slash_frame_idx = 0
        self.front_slash_anim_timer = 0
        self.front_slash_anim_speed = 200  # ms per frame
        self.split_started = False
        self.split_start_time = 0
        self.split_offset = 0
        self.pre_split_surface = None
        self.knight_y = self.knight_pos[1]
        self.knight_trail = []
        self.trail_length = 13
        self.trail_alphas = [80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 30, 25, 20]
        self.rise_start_time = 0
        self.front_slash_anim_done = False

        

    def run(self):
        running = True
        clock = self.clock or pygame.time.Clock()
        start_time = pygame.time.get_ticks()
        self.aura_anim_timer = 0  # For animated aura
        w,h = self.screen_rect.width, self.screen_rect.height
        phase1_start_time = None
        phase2_start_time = None
        # Number of segments
        N = 36  # for width
        M = 24  # for height

        # Spiral 1: bottom, right, top, left (counter-clockwise)
        spiral1_pos = []
        # Bottom edge (left to right)
        for i in range(N):
            spiral1_pos.append((w * i / (N-1), h))
        # Right edge (bottom to top)
        for i in range(1, M):
            spiral1_pos.append((w, h - h * i / (M-1)))
        # Top edge (right to left)
        for i in range(1, N):
            spiral1_pos.append((w - w * i / (N-1), 0))
        # Left edge (top to bottom)
        for i in range(1, M-1):
            spiral1_pos.append((0, h * i / (M-1)))

        # Spiral 2: top, left, bottom, right (counter-clockwise)
        spiral2_pos = []
        # Top edge (right to left)
        for i in range(N):
            spiral2_pos.append((w - w * i / (N-1), 0))
        # Left edge (top to bottom)
        for i in range(1, M):
            spiral2_pos.append((0, h * i / (M-1)))
        # Bottom edge (left to right)
        for i in range(1, N):
            spiral2_pos.append((w * i / (N-1), h))
        # Right edge (bottom to top)
        for i in range(1, M-1):
            spiral2_pos.append((w, h - h * i / (M-1)))
        blacked_out = False
        while running:
            dt = clock.tick(60)
            now = pygame.time.get_ticks() - start_time
            self.aura_anim_timer += dt
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            # Handle player input (movement) during attack phases (every frame, not just on events)
            if self.state >= 1:
                keys = pygame.key.get_pressed()
                speed = self.player_speed
                if keys[pygame.K_LEFT]:
                    self.player_x -= speed
                if keys[pygame.K_RIGHT]:
                    self.player_x += speed
                if keys[pygame.K_UP]:
                    self.player_y -= speed
                if keys[pygame.K_DOWN]:
                    self.player_y += speed
                    # Clamp to screen bounds
                    self.player_x = max(0, min(self.player_x, self.screen_rect.width - self.heart_size))
                    self.player_y = max(0, min(self.player_y, self.screen_rect.height - self.heart_size))
            # Fade out background in sync with box
            if self.state == 0:
                progress = min(1.0, now / self.box_expand_duration)
                self.box_scale = 1.0 + (self.box_target_scale - 1.0) * progress
                self.box_alpha = int(255 * (1.0 - progress))
                self.bg_alpha = self.box_alpha  # Sync bg fade with box
                self.draw_fading_bg()
                self.draw_expanding_box()
                self.draw_heart()
                if progress >= 1.0:
                    # Erase everything and fill black before continuing
                    self.screen.fill((0, 0, 0))
                    pygame.display.flip()
                    blacked_out = True
                    self.state = 1
                    self.timer = now
                    continue  # Skip the rest of this frame to ensure black fill
            elif self.state == 1:
                # Knight fade in and drift down
                knight_fade_time = 1000  # ms
                knight_progress = min(1.0, (now - self.timer) / knight_fade_time)
                if blacked_out:
                    self.screen.fill((0, 0, 0))
                else:
                    self.draw_fading_bg(final=True)
                self.draw_knight_with_aura(fade=knight_progress)
                self.draw_heart()
                if knight_progress >= 1.0:
                    self.state = 2  # Ready for phase 1

            elif self.state == 2:
                # PHASE 1: Stars spawn and move toward knight
                if phase1_start_time is None:
                    phase1_start_time = now
                    self.phase1_star_count = 0  # Track how many stars have spawned
                    self.phase1_total_stars = 20  # Or however many you want in this phase
                    self.phase1_base_duration = self.star_duration
                    self.phase1_base_interval = self.star_spawn_interval
                    # Play absorb sound effect once for the duration of phase 1 + phase 2
                    if not self.absorb_sfx_played:
                        total_duration = self.phase1_duration + self.phase2_duration
                        self.absorb_sfx.play(maxtime=total_duration)
                        self.absorb_sfx_played = True
                self.draw_fading_bg(final=True)
                self.draw_knight_with_aura(fade=1.0)
                invincible = hasattr(self, 'invincible_until') and pygame.time.get_ticks() < self.invincible_until
                if invincible:
                    if ((pygame.time.get_ticks() // 100) % 2) == 0:
                        heart_draw_img = self.heart_img_0
                    else:
                        heart_draw_img = self.heart_img_1
                else:
                    heart_draw_img = self.heart_img_0
                self.screen.blit(heart_draw_img, (self.player_x, self.player_y))
                # Spawn stars at random perimeter points
                if (now - self.last_star_spawn > self.star_spawn_interval and
                    self.phase1_star_count < self.phase1_total_stars and
                    now - phase1_start_time < self.phase1_duration):
                    w, h = self.screen_rect.width, self.screen_rect.height
                    edge = random.choice(['top','bottom','left','right'])
                    if edge == 'top':
                        x = random.randint(0, w)
                        y = 0
                    elif edge == 'bottom':
                        x = random.randint(0, w)
                        y = h
                    elif edge == 'left':
                        x = 0
                        y = random.randint(0, h)
                    else:
                        x = w
                        y = random.randint(0, h)
                    start_pos = (x, y)
                    end_pos = self.knight_pos
                    # Curve offset: pick a control point between start and end, offset by up to 200px
                    mx, my = (x + end_pos[0]) / 2, (y + end_pos[1]) / 2
                    offset_angle = random.uniform(0, 2*math.pi)
                    offset_radius = random.uniform(80, 200)
                    cx = mx + offset_radius * math.cos(offset_angle)
                    cy = my + offset_radius * math.sin(offset_angle)
                    # Make each next star faster (lower duration)
                    star_duration = max(350, int(self.phase1_base_duration * (0.96 ** self.phase1_star_count)))
                    star = self.Star(self.star_img, start_pos, end_pos, (cx, cy), self.star_scale, self.min_star_scale, star_duration)
                    self.stars.append(star)
                    # Reduce interval for next star, min 50ms
                    self.star_spawn_interval = max(50, int(self.phase1_base_interval * (0.96 ** self.phase1_star_count)))
                    self.last_star_spawn = now
                    self.phase1_star_count += 1
                player_rect = pygame.Rect(self.player_x, self.player_y, self.heart_size, self.heart_size)
                hit_this_frame = False
                # Update and draw stars
                for star in self.stars:
                    star.update(pygame.time.get_ticks())
                    star.draw(self.screen)
                    if not hasattr(self, 'invincible_until') or pygame.time.get_ticks() >= self.invincible_until:
                        if star.get_hitbox().colliderect(player_rect):
                            hit_this_frame = True
                # Remove finished stars
                self.stars = [s for s in self.stars if not s.done]
                # Handle hit and invincibility
                if hit_this_frame and not invincible:
                    self.player_lives = max(0, self.player_lives - 1)
                    self.invincible_until = pygame.time.get_ticks() + 1000  # 1 second invincibility
                if now - phase1_start_time > self.phase1_duration:
                    self.state = 3  # Next phase

            elif self.state == 3:
                # PHASE 2: Spiral stars
                if phase2_start_time is None:
                    phase2_start_time = now
                    self.spiral_stars_spawned = False
                    w, h = self.screen_rect.width, self.screen_rect.height
                    knight_pos = self.knight_pos # I forgot why it's here but there's an error when I remove it
                    # User-defined spiral positions (4 pairs)
                    self.spiral_star_pairs = list(zip(spiral1_pos, spiral2_pos))
                    self.spiral_star_spawn_idx = 0
                    self.spiral_star_spawn_interval = 30  # ms between pairs
                    self.spiral_star_last_spawn = now
                    self.active_spiral_stars = []
                    self.spiral_stars_spawned = True
                # Draw phase 2
                self.screen.fill((0, 0, 0))
                self.draw_knight_with_aura(fade=1.0)
                invincible = hasattr(self, 'invincible_until') and pygame.time.get_ticks() < self.invincible_until
                if invincible:
                    if ((pygame.time.get_ticks() // 100) % 2) == 0:
                        heart_draw_img = self.heart_img_0
                    else:
                        heart_draw_img = self.heart_img_1
                else:
                    heart_draw_img = self.heart_img_0
                self.screen.blit(heart_draw_img, (self.player_x, self.player_y))
                now_abs = pygame.time.get_ticks()
                # Spawn next pair if needed
                if self.spiral_stars_spawned and self.spiral_star_spawn_idx < len(self.spiral_star_pairs):
                    if now_abs - self.spiral_star_last_spawn >= self.spiral_star_spawn_interval or self.spiral_star_spawn_idx == 0:
                        pair = self.spiral_star_pairs[self.spiral_star_spawn_idx]
                        for start_pos in pair:
                            star = self.SpiralStar(self.star_img, start_pos, self.knight_pos, self.spiral_star_scale, self.min_star_scale, self.spiral_star_duration)
                            self.active_spiral_stars.append(star)
                        self.spiral_star_spawn_idx += 1
                        self.spiral_star_last_spawn = now_abs
                player_rect = pygame.Rect(self.player_x, self.player_y, self.heart_size, self.heart_size)
                hit_this_frame = False        
                # Update and draw all active spiral stars
                for star in self.active_spiral_stars:
                    star.update(now_abs)
                    star.draw(self.screen)
                    if not hasattr(self, 'invincible_until') or pygame.time.get_ticks() >= self.invincible_until:
                        if star.get_hitbox().colliderect(player_rect):
                            hit_this_frame = True
                # Remove finished spiral stars
                self.active_spiral_stars = [s for s in self.active_spiral_stars if not s.done]
                # Handle hit and invincibility
                if hit_this_frame and not invincible:
                    self.player_lives = max(0, self.player_lives - 1)
                    self.invincible_until = pygame.time.get_ticks() + 1000  # 1 second invincibility
                # End phase after last pair is spawned and all stars are done
                if self.spiral_star_spawn_idx >= len(self.spiral_star_pairs) and not self.active_spiral_stars:
                    self.state = 4  # Next phase

            elif self.state == 4:
                # Clear all stars
                self.stars = []
                self.spiral_stars = []
                self.active_spiral_stars = []
                self.screen.fill((0, 0, 0))  # Or draw your background if needed

                # Animate the flourish
                now_ticks = pygame.time.get_ticks()
                if not hasattr(self, 'flourish_anim_start'):
                    self.flourish_anim_start = now_ticks
                    self.flourish_frame_idx = 0
                    self.flourish_paused = False
                    self.flourish_pause_start = 0
                    self.flourish_fadein = False
                    self.flourish_fadein_start = 0

                # Handle pause and fade logic
                if self.flourish_frame_idx == 5 and not self.flourish_paused:
                    # Start pause
                    self.flourish_paused = True
                    self.flourish_pause_start = now_ticks

                if self.flourish_paused:
                    # During pause, fade out completely, then fade in to 75%
                    pause_elapsed = now_ticks - self.flourish_pause_start
                    if pause_elapsed < self.flourish_pause_duration:
                        alpha = 0  # Fully transparent
                    elif pause_elapsed < self.flourish_pause_duration + self.flourish_fadein_duration:
                        self.flourish_fadein = True
                        self.flourish_fadein_start = self.flourish_pause_start + self.flourish_pause_duration
                        # Fade in from 0 to 191 (75%)
                        fadein_elapsed = pause_elapsed - self.flourish_pause_duration
                        alpha = int(191 * (fadein_elapsed / self.flourish_fadein_duration))
                    else:
                        # End pause and fade-in, set frame 5 to 75% alpha, resume animation
                        self.flourish_paused = False
                        self.flourish_fadein = False
                        alpha = 191
                        # Advance to next frame after fade-in
                        self.flourish_anim_start += (self.flourish_pause_duration + self.flourish_fadein_duration)
                        self.flourish_frame_idx += 1
                else:
                    # Normal frame advancement
                    if now_ticks - self.flourish_anim_start > self.flourish_frame_idx * self.flourish_anim_speed:
                        self.flourish_frame_idx += 1

                    # Determine alpha for current frame
                    if self.flourish_frame_idx <= 1:
                        alpha = 255
                    elif 2 <= self.flourish_frame_idx < 5:
                        # Fade from 255 to 51 over frames 2-5
                        alpha = int(255 - ((self.flourish_frame_idx - 2) / 3) * (255 - 51))
                    elif self.flourish_frame_idx == 5:
                        alpha = 191 if not self.flourish_fadein else alpha  # 75% after fade-in
                    else:
                        alpha = 255

                if self.flourish_frame_idx >= len(self.flourish_frames) - 1:
                    self.flourish_frame_idx = len(self.flourish_frames) - 1
                    if not self.roar_sfx_played:
                        self.roar_sfx.play()
                        self.roar_sfx_played = True
                    self.state = 5

                flourish_img = self.flourish_frames[self.flourish_frame_idx].copy()
                flourish_img.set_alpha(alpha)
                flourish_rect = flourish_img.get_rect(center=self.knight_pos)
                self.screen.blit(flourish_img, flourish_rect)

                # Draw the heart (with invincibility flash)
                invincible = hasattr(self, 'invincible_until') and pygame.time.get_ticks() < self.invincible_until
                if invincible:
                    if ((pygame.time.get_ticks() // 100) % 2) == 0:
                        heart_draw_img = self.heart_img_0
                    else:
                        heart_draw_img = self.heart_img_1
                else:
                    heart_draw_img = self.heart_img_0
                self.screen.blit(heart_draw_img, (self.player_x, self.player_y))

            elif self.state == 5:
                self.screen.fill((0, 0, 0))
                now_ticks = pygame.time.get_ticks()
                if not hasattr(self, 'roar_anim_start'):
                    self.roar_anim_start = now_ticks
                    self.roar_phase_start_time = now_ticks
                    self.roar_star_count = 0
                
                # Check if roar has ended
                roar_elapsed = now_ticks - self.roar_anim_start
                if roar_elapsed >= self.roar_duration and not self.stars_returning:
                    self.stars_returning = True
                    for star in self.roar_stars:
                        star.state = 'slight_return'
                        star.starchild_up_img = self.starchild_up
                        star.starchild_down_img = self.starchild_down
                        star.state = 'slight_return'
                        star.return_start = now_ticks
                        star.transform_frames = self.star_transform_frames
                    
                    # After star return starts, handle reverse flourish
                    if not self.reverse_flourish_started:
                        self.reverse_flourish_started = True
                        self.reverse_flourish_start_time = now_ticks
                        # Create reverse frames (reverse the flourish animation)
                        self.reverse_flourish_frames = self.flourish_frames[::-1]
                        self.reverse_flourish_frame_idx = 0
                        self.reverse_flourish_anim_speed = 150  # Slowed down from 100 to 150ms per frame to match star return duration
                
                # Handle reverse flourish animation
                reverse_flourish_done = False
                if self.reverse_flourish_started:
                    reverse_elapsed = now_ticks - self.reverse_flourish_start_time
                    if reverse_elapsed > self.reverse_flourish_frame_idx * self.reverse_flourish_anim_speed:
                        self.reverse_flourish_frame_idx += 1
                    
                    if self.reverse_flourish_frame_idx >= len(self.reverse_flourish_frames):
                        reverse_flourish_done = True
                        # Always draw the last frame after animation is done
                        reverse_img = self.reverse_flourish_frames[-1]
                        reverse_rect = reverse_img.get_rect(center=self.knight_pos)
                        self.screen.blit(reverse_img, reverse_rect)
                    else:
                        # Draw reverse flourish
                        reverse_img = self.reverse_flourish_frames[self.reverse_flourish_frame_idx]
                        reverse_rect = reverse_img.get_rect(center=self.knight_pos)
                        self.screen.blit(reverse_img, reverse_rect)
                
                # Spawn stars at intervals, only during the first 8 seconds of the roar
                if roar_elapsed < self.roar_duration:
                    # Calculate accelerating spawn interval and star duration
                    acceleration = self.roar_acceleration_factor ** self.roar_star_count
                    current_spawn_interval = max(150, int(self.roar_base_spawn_interval * acceleration))
                    current_star_duration = max(800, int(self.roar_base_duration * acceleration))
                    
                    if now_ticks - self.last_roar_star_spawn > current_spawn_interval:
                        # Pick a random point on the outline of the battle box
                        w, h = self.screen_rect.width, self.screen_rect.height
                        edge = random.choice(['bottom', 'left', 'right'])
                        if edge == 'bottom':
                            x = random.randint(0, w)
                            y = h
                        elif edge == 'left':
                            x = 0
                            y = random.randint(0, h)
                        else:
                            x = w
                            y = random.randint(0, h)
                        end_pos = (x, y)
                        start_pos = self.knight_pos
                        star = self.RoarStar(self.roar_star_img, start_pos, end_pos, self.roar_star_min_scale, self.roar_star_max_scale, current_star_duration)
                        self.roar_stars.append(star)
                        self.last_roar_star_spawn = now_ticks
                        self.roar_star_count += 1    
                
                # Draw the heart (with invincibility flash)
                invincible = hasattr(self, 'invincible_until') and pygame.time.get_ticks() < self.invincible_until
                if invincible:
                    if ((pygame.time.get_ticks() // 100) % 2) == 0:
                        heart_draw_img = self.heart_img_0
                    else:
                        heart_draw_img = self.heart_img_1
                else:
                    heart_draw_img = self.heart_img_0
                # Always update and draw all roar stars
                for star in self.roar_stars:
                    star.update(now_ticks)
                    star.draw(self.screen)
                # Remove finished stars
                self.roar_stars = [s for s in self.roar_stars if not s.done]
                # Heart rect for collision (scaled image assumed)
                hit_this_frame = False
                heart_rect = heart_draw_img.get_rect(topleft=(self.player_x, self.player_y))

                # Check collision with all roar stars and their starchilds
                for star in self.roar_stars:
                    hitbox = star.get_hitbox()
                    if hitbox and hitbox.colliderect(heart_rect):
                        hit_this_frame = True

                    if star.state == 'exploded':
                        for starchild in star.starchilds:
                            sc_hitbox = starchild.get_hitbox()
                            if sc_hitbox and sc_hitbox.colliderect(heart_rect):
                                hit_this_frame = True
                # Only end the attack when both reverse flourish and all stars are done
                if reverse_flourish_done and not self.roar_stars:
                    self.explosion_time = pygame.time.get_ticks()
                    self.explosion_time_recorded = True
                    self.state = 6
                    self.state6_start_time = pygame.time.get_ticks()
                # Draw roar animation only if not in reverse flourish
                if not self.reverse_flourish_started:
                    frame = ((now_ticks - self.roar_anim_start) // self.roar_anim_speed) % len(self.roar_frames)
                    roar_img = self.roar_frames[frame]
                    roar_rect = roar_img.get_rect(center=self.knight_pos)
                    self.screen.blit(roar_img, roar_rect)
                if hit_this_frame and not invincible:
                    self.player_lives = max(0, self.player_lives - 1)
                    self.invincible_until = pygame.time.get_ticks() + 1000  # 1 second invincibility
                
                self.screen.blit(heart_draw_img, (self.player_x, self.player_y))

            elif self.state == 6:
                now = pygame.time.get_ticks()
                self.screen.fill((0, 0, 0))  # Clear the screen to black
                front_slash_img = self.front_slash_frames[0]
                front_slash_rect = front_slash_img.get_rect(center=self.knight_pos)
                invincible = hasattr(self, 'invincible_until') and pygame.time.get_ticks() < self.invincible_until
                if invincible:
                    if ((pygame.time.get_ticks() // 100) % 2) == 0:
                        heart_draw_img = self.heart_img_0
                    else:
                        heart_draw_img = self.heart_img_1
                else:
                    heart_draw_img = self.heart_img_0

                time_since_explosion = now - self.explosion_time
                progress = min(1.0, time_since_explosion / self.slash_duration)
                print(f"Progress: {progress}")

                # Determine width scaling (only in second half)
                if progress < 0.5:
                    scale_x = 1.0
                else:
                    shrink_progress = (progress - 0.5) / 0.5
                    scale_x = 1.0 - 0.7 * shrink_progress

                if progress >= 0.5:
                    if now - self.front_slash_anim_timer >= self.front_slash_anim_speed:
                        self.front_slash_frame_idx += 1
                        self.front_slash_anim_timer = now
                    if self.front_slash_frame_idx >= (len(self.front_slash_frames) - 1):
                        self.front_slash_frame_idx = len(self.front_slash_frames) - 2  # hold on last frame (not glow image) for exit sequence
                        if not self.front_slash_anim_done:
                            self.front_slash_anim_done = True
                            self.rise_start_time = now
                    front_slash_img = self.front_slash_frames[self.front_slash_frame_idx]
                else:
                    front_slash_img = self.front_slash_frames[0]  # idle frame

                
                scaled_width = max(1, int(self.target_width * scale_x))
                scaled_surf = pygame.transform.smoothscale(self.diagonal_slash_img, (scaled_width, self.target_height))
                
                dx = 0.10 * self.screen_width
                dy = self.screen_height
                angle = -math.degrees(math.atan2(dy, dx)) + 90
                rotated_slash = pygame.transform.rotate(scaled_surf, angle)


                # Now crop it vertically from the bottom
                crop_progress = min(1.0, progress / 0.5)  # goes from 0 to 1 in the first half
                visible_height = int(rotated_slash.get_height() * crop_progress)
                if visible_height <= 0:
                    pass
                cropped_surf = pygame.Surface((rotated_slash.get_width(), visible_height), pygame.SRCALPHA)
                cropped_surf.blit(rotated_slash, (0, 0), area=pygame.Rect(0, 0, rotated_slash.get_width(), visible_height))

                # Draw
                target_center_x = 0.5 * self.screen_width
                target_center_y = self.screen_height // 2
                rotated_rect = cropped_surf.get_rect(center=(target_center_x, target_center_y))

                if not hasattr(self, 'rise_start_time') and self.front_slash_frame_idx >= len(self.front_slash_frames) - 2:
                    self.rise_start_time = pygame.time.get_ticks()


                self.screen.blit(cropped_surf, rotated_rect.topleft)
                if progress < 1.0:
                    self.screen.blit(front_slash_img, front_slash_rect)
                else:
                    if not self.front_slash_anim_done:
                        self.front_slash_anim_done = True
                        self.rise_start_time = now
                    if now - self.rise_start_time < 500:
                        self.screen.blit(front_slash_img, front_slash_rect)
                    else:
                        rise_speed = 8  # pixels per frame
                        self.knight_y -= rise_speed

                        # Add current position to the trail
                        self.knight_trail.insert(0, self.knight_y)
                        if len(self.knight_trail) > self.trail_length:
                            self.knight_trail.pop()

                        # Draw trail (downwards)
                        for i, trail_y in enumerate(self.knight_trail):
                            if i < len(self.trail_alphas):
                                trail_surf = front_slash_img.copy()
                                trail_surf.set_alpha(self.trail_alphas[i])
                                trail_rect = trail_surf.get_rect(center=(self.knight_pos[0], trail_y))
                                self.screen.blit(trail_surf, trail_rect)

                        # Draw the knight (main image)
                        main_knight_rect = front_slash_img.get_rect(center=(self.knight_pos[0], self.knight_y))
                        self.screen.blit(front_slash_img, main_knight_rect)
                        
                        # Optional: exit when fully offscreen
                        if self.knight_y + front_slash_img.get_height() < 0:
                            self.state = 7  # or your next state
                self.screen.blit(heart_draw_img, (self.player_x, self.player_y))
            
            # Draw lives counter
            lives_surf = self.font.render(f"LIVES: {self.player_lives}", True, (255, 255, 255))
            self.screen.blit(lives_surf, (50, 50))
            pygame.display.flip()

    def draw_fading_bg(self, final=False):
        # Fade out bg_img using alpha
        bg = self.bg_img.copy()
        alpha = self.bg_alpha if not final else 0
        if alpha < 255:
            fade_surf = pygame.Surface(bg.get_size(), pygame.SRCALPHA)
            fade_surf.fill((0, 0, 0, 255 - alpha))
            bg.blit(fade_surf, (0, 0))
        self.screen.blit(bg, (0, 0))

    def draw_knight_with_aura(self, fade=1.0):
        # Animated, shrinking (inward) aura with 3 layers
        scale_factor = 2.25  # Current size
        drift_start = -30
        drift_end = 0
        drift = drift_start * (1 - fade) + drift_end * fade
        alpha = int(255 * fade)
        pos = (self.knight_pos[0], self.knight_pos[1] + drift)
        # Aura animation parameters
        aura_layers = 3
        aura_cycle_ms = 1200  # How long for a full pulse
        base_scale = 1.1 * scale_factor
        max_scale = 2.0 * scale_factor
        for i in range(aura_layers):
            # Each layer is offset in phase
            phase = (self.aura_anim_timer / aura_cycle_ms + i / aura_layers) % 1.0
            # REVERSE: start large, shrink to small
            scale = max_scale - (max_scale - base_scale) * phase
            aura_alpha = int(90 * phase * fade)  # Fade in as it shrinks
            glow = pygame.transform.smoothscale(self.knight_glow_img, (
                int(self.knight_glow_img.get_width() * scale),
                int(self.knight_glow_img.get_height() * scale)))
            glow.set_alpha(aura_alpha)
            glow_rect = glow.get_rect(center=pos)
            self.screen.blit(glow, glow_rect)
        # Draw knight
        knight = pygame.transform.smoothscale(self.knight_img, (
            int(self.knight_img.get_width() * scale_factor),
            int(self.knight_img.get_height() * scale_factor)))
        knight.set_alpha(alpha)
        knight_rect = knight.get_rect(center=pos)
        self.screen.blit(knight, knight_rect)

    def draw_expanding_box(self):
        # Calculate new rect
        w = int(self.battle_box_rect.width * self.box_scale)
        h = int(self.battle_box_rect.height * self.box_scale)
        rect = pygame.Rect(0, 0, w, h)
        rect.center = self.box_center
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((*self.battle_box_color, self.box_alpha))
        self.screen.blit(s, rect)
        # Optionally draw border
        if self.box_alpha > 0:
            border_s = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(border_s, (*self.battle_box_border_color, self.box_alpha), border_s.get_rect(), self.battle_box_border)
            self.screen.blit(border_s, rect)

    def draw_heart(self):
        heart_img = self.heart_img_0
        heart_rect = heart_img.get_rect(center=(self.player_x, self.player_y))
        self.screen.blit(heart_img, heart_rect)
    
    # helper function for the end of state 6
    def point_side(px, py, x1, y1, x2, y2):
        # Returns >0 if point is on one side, <0 if other
        return (x2 - x1)*(py - y1) - (y2 - y1)*(px - x1)

    class Star:
        def __init__(self, img, start_pos, end_pos, curve_offset, star_scale, min_star_scale, duration=1200):
            self.img = img
            self.start_pos = start_pos
            self.end_pos = end_pos
            self.curve_offset = curve_offset  # (cx, cy) for control point
            self.spawn_time = pygame.time.get_ticks()
            self.duration = duration
            self.done = False
            self.current_pos = start_pos
            self.star_scale = star_scale
            self.min_star_scale = min_star_scale
            self.scale = star_scale
        def update(self, now):
            t = min(1.0, (now - self.spawn_time) / self.duration)
            # Quadratic Bezier: B(t) = (1-t)^2*P0 + 2*(1-t)*t*C + t^2*P1
            x0, y0 = self.start_pos
            x1, y1 = self.end_pos
            cx, cy = self.curve_offset
            bx = (1-t)**2 * x0 + 2*(1-t)*t*cx + t**2 * x1
            by = (1-t)**2 * y0 + 2*(1-t)*t*cy + t**2 * y1
            self.current_pos = (bx, by)
            self.scale = self.star_scale - (self.star_scale - self.min_star_scale) * t
            if t >= 1.0:
                self.done = True
        def draw(self, screen):
            img = pygame.transform.smoothscale(self.img, (
                int(self.img.get_width() * self.scale),
                int(self.img.get_height() * self.scale)))
            rect = img.get_rect(center=(int(self.current_pos[0]), int(self.current_pos[1])))
            screen.blit(img, rect)
        def get_hitbox(self):
            img_w = int(self.img.get_width() * self.scale)
            img_h = int(self.img.get_height() * self.scale)
            rect = pygame.Rect(0, 0, img_w, img_h)
            rect.center = (int(self.current_pos[0]), int(self.current_pos[1]))
            return rect

    class SpiralStar:
        def __init__(self, img, start_pos, end_pos, star_scale, min_star_scale, duration=1200):
            self.img = img
            self.start_pos = start_pos
            self.end_pos = end_pos
            self.spawn_time = pygame.time.get_ticks()
            self.duration = duration
            self.done = False
            self.current_pos = start_pos
            self.star_scale = star_scale
            self.min_star_scale = min_star_scale
            self.scale = star_scale
        def update(self, now):
            t = min(1.0, (now - self.spawn_time) / self.duration)
            # Linear interpolation
            x0, y0 = self.start_pos
            x1, y1 = self.end_pos
            bx = x0 + (x1 - x0) * t
            by = y0 + (y1 - y0) * t
            self.current_pos = (bx, by)
            self.scale = self.star_scale - (self.star_scale - self.min_star_scale) * t
            if t >= 1.0:
                self.done = True
        def draw(self, screen):
            img = pygame.transform.smoothscale(self.img, (
                int(self.img.get_width() * self.scale),
                int(self.img.get_height() * self.scale)))
            rect = img.get_rect(center=(int(self.current_pos[0]), int(self.current_pos[1])))
            screen.blit(img, rect)
        def get_hitbox(self):
            img_w = int(self.img.get_width() * self.scale)
            img_h = int(self.img.get_height() * self.scale)
            rect = pygame.Rect(0, 0, img_w, img_h)
            rect.center = (int(self.current_pos[0]), int(self.current_pos[1]))
            return rect

    class RoarStar:
        def __init__(self, img, start_pos, end_pos, min_scale, max_scale, duration):
            self.img = img
            self.start_pos = start_pos
            self.end_pos = end_pos
            self.spawn_time = pygame.time.get_ticks()
            self.duration = duration
            self.done = False
            self.current_pos = start_pos
            self.min_scale = min_scale
            self.max_scale = max_scale * 0.85 
            self.scale = min_scale
            # Simple state machine
            self.state = 'moving_out'  # States: moving_out, slight_return, transforming, exploded
            self.return_speed = 6  # Slowed down from 12 to 6 for a slower return
            self.starchilds = []
            self.explode_scale_start = self.max_scale
            self.explode_scale_end = self.min_scale * 0.7  # Shrink even smaller on explosion
            self.explode_anim_total = 4  # Number of transform frames
            self.explode_anim_progress = 0

        def is_on_screen(self):
            # Add a small margin around the screen
            margin = 50
            x, y = self.current_pos
            return (-margin <= x <= 1920 + margin and 
                   -margin <= y <= 1080 + margin)
                
        def start_return(self, transform_frames, starchild_up_img, starchild_down_img):
            if self.state == 'moving_out':
                self.state = 'slight_return'
                self.return_start = pygame.time.get_ticks()
                self.transform_frames = transform_frames
                # Store images for starchild creation
                self.starchild_up_img = starchild_up_img
                self.starchild_down_img = starchild_down_img
            elif self.state == 'moving_out':
                # If star is off screen, mark it as done
                self.done = True
                
        def create_starchilds(self):
            now = pygame.time.get_ticks() if hasattr(pygame, 'time') else 0
            scx, scy = self.current_pos
            speed = getattr(self, 'starchild_speed', 8)

            directions_with_angles = [
                ((0, -1), 0, self.starchild_up_img),     # Up
                ((1, 1), 45, self.starchild_down_img),   # Down-right
                ((-1, 1), -45, self.starchild_down_img), # Down-left
                ((0, 1), 0, self.starchild_down_img),  # Down
                ((1, -1), -45, self.starchild_up_img),   # Up-right
                ((-1, -1), 45, self.starchild_up_img),   # Up-left
            ]

            for (dx, dy), angle, base_img in directions_with_angles:
                norm = math.hypot(dx, dy)
                vx, vy = dx / norm, dy / norm
                rotated_img = pygame.transform.rotate(base_img, angle)
                self.starchilds.append(self.StarChild(rotated_img, (scx, scy), (vx, vy), speed=speed))

            self.state = 'exploded'

        def get_hitbox(self):
            if self.state in ['moving_out', 'slight_return']:
                img = pygame.transform.smoothscale(
                    self.img, (
                        int(self.img.get_width() * self.scale),
                        int(self.img.get_height() * self.scale)
                    )
                )
                return img.get_rect(center=(int(self.current_pos[0]), int(self.current_pos[1])))
            return None  # No hitbox during transform or explosion

        class StarChild:
            def __init__(self, img, start_pos, direction, speed=5):
                self.img = img
                self.pos = list(start_pos)  # Convert to list for mutable updates
                self.direction = direction  # Normalized direction vector
                self.speed = speed
                self.done = False
                self.w, self.h = pygame.display.get_surface().get_width(), pygame.display.get_surface().get_height()
                
            def update(self):
                self.pos[0] += self.direction[0] * self.speed
                self.pos[1] += self.direction[1] * self.speed
                # Mark as done if off screen
                if (self.pos[0] < -50 or self.pos[0] > self.w + 50 or 
                    self.pos[1] < -50 or self.pos[1] > self.h + 50):
                    self.done = True
                    
            def draw(self, screen):
                # Scale the image to double size
                scaled_img = pygame.transform.scale(self.img, (self.img.get_width() * 2, self.img.get_height() * 2))
                rect = scaled_img.get_rect(center=(int(self.pos[0]), int(self.pos[1])))
                screen.blit(scaled_img, rect)
            
            def get_hitbox(self):
                scaled_img = pygame.transform.scale(
                    self.img,
                    (self.img.get_width() * 2, self.img.get_height() * 2)
                )
                return scaled_img.get_rect(center=(int(self.pos[0]), int(self.pos[1])))

            
        def update(self, now):
            if self.state == 'moving_out':
                t = min(1.0, (now - self.spawn_time) / self.duration)
                grow_t = max(0.0, t) ** 0.25  # More gradual growth
                x0, y0 = self.start_pos
                x1, y1 = self.end_pos
                dx = x1 - x0
                dy = y1 - y0
                length = (dx * dx + dy * dy) ** 0.5
                if length > 0:
                    dx = dx / length
                    dy = dy / length
                    
                t = (now - self.spawn_time) / self.duration
                speed = length / self.duration  # pixels per millisecond
                move_dist = speed * (now - self.spawn_time)
                
                # Keep moving at constant speed
                self.current_pos = (x0 + dx * move_dist, y0 + dy * move_dist)
                
                # Scale grows quickly then stays constant
                grow_t = min(1.0, t * 4)  # Reach full size in 1/4 of the duration
                self.scale = float(self.min_scale + (self.max_scale - self.min_scale) * grow_t)

            elif self.state == 'slight_return':
            # Move a bit toward the knight, then switch to 'transforming'
                if not hasattr(self, 'return_start'):
                    self.return_start = now

                return_duration = 800  # Increased from 300 to 800ms for longer return movement
                progress = (now - self.return_start) / return_duration

                if progress >= 1.0:
                    self.state = 'transforming'
                    self.transform_frame_idx = 0
                    self.explode_anim_progress = 0
                else:
                    x1, y1 = self.current_pos
                    x2, y2 = self.start_pos
                    dx = x2 - x1
                    dy = y2 - y1
                    dist = (dx ** 2 + dy ** 2) ** 0.5
                    if dist > 0:
                        dx /= dist
                        dy /= dist
                    # Move back with easing
                    move_dist = self.return_speed * (1 - (progress ** 2))  # Added easing for smoother movement
                    self.current_pos = (x1 + dx * move_dist, y1 + dy * move_dist)
                    
            elif self.state == 'transforming':
                # Slow down the transform animation
                if not hasattr(self, 'transform_timer'):
                    self.transform_timer = now
                    self.transform_frame_idx = 0
                    self.explode_anim_progress = 0
            
                if now - self.transform_timer > 150:  # 150ms per frame
                    self.transform_frame_idx += 1
                    self.transform_timer = now
                    self.explode_anim_progress += 1
                    
                # Scale down as it explodes
                t = min(1.0, self.explode_anim_progress / self.explode_anim_total)
                self.scale = self.explode_scale_start + (self.explode_scale_end - self.explode_scale_start) * t
                if self.transform_frame_idx >= 4:  # 4 frames in bullet star animation
                    self.create_starchilds()

            elif self.state == 'exploded':
                # Continue scaling down for a few frames after explosion
                if self.explode_anim_progress < self.explode_anim_total:
                    t = min(1.0, self.explode_anim_progress / self.explode_anim_total)
                    self.scale = self.explode_scale_start + (self.explode_scale_end - self.explode_scale_start) * t
                    self.explode_anim_progress += 1
                # Update starchilds
                for starchild in self.starchilds:
                    starchild.update()
                # Remove finished starchilds
                self.starchilds = [s for s in self.starchilds if not s.done]
                if not self.starchilds:
                    self.done = True
                    
        def draw(self, screen):
            if self.state in ['moving_out', 'slight_return']:
                img = pygame.transform.smoothscale(self.img, (
                    int(self.img.get_width() * self.scale),
                    int(self.img.get_height() * self.scale)))
                rect = img.get_rect(center=(int(self.current_pos[0]), int(self.current_pos[1])))
                screen.blit(img, rect)
            elif self.state == 'transforming':
                # Keep same size during transform animation, but scale down
                img = self.transform_frames[min(self.transform_frame_idx, len(self.transform_frames) - 1)]
                img = pygame.transform.smoothscale(img, (
                    int(img.get_width() * self.scale),
                    int(img.get_height() * self.scale)))
                rect = img.get_rect(center=(int(self.current_pos[0]), int(self.current_pos[1])))
                screen.blit(img, rect)
            elif self.state == 'exploded':
                # Draw the shrinking star for a few frames, then only starchilds
                if self.explode_anim_progress < self.explode_anim_total:
                    img = self.transform_frames[-1]
                    img = pygame.transform.smoothscale(img, (
                        int(img.get_width() * self.scale),
                        int(img.get_height() * self.scale)))
                    rect = img.get_rect(center=(int(self.current_pos[0]), int(self.current_pos[1])))
                    screen.blit(img, rect)
                for starchild in self.starchilds:
                    starchild.draw(screen)

def make_attack_for_debug(attack_name):
    """
    Helper for debugging: returns a ready-to-run attack instance for the given attack_name (e.g., 'Attack1').
    Sets up a minimal environment and loads all required assets.
    """
    pygame.init()
    screen_width, screen_height = 1920, 1080
    screen = pygame.display.set_mode((screen_width, screen_height))
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bg_path = os.path.join(base_dir, 'sprites', 'spr_knight_snow_bg.png')
    bg_img = pygame.image.load(bg_path).convert()
    bg_img = pygame.transform.scale(bg_img, (screen_width, screen_height))
    # Fountain
    fountain_dir = os.path.join(base_dir, 'sprites', 'spr_fountainbg')
    fountain_files = [os.path.join(fountain_dir, f'spr_cc_fountainbg_{i}.png') for i in range(4)]
    fountain_frames = [pygame.image.load(f).convert_alpha() for f in fountain_files]
    fountain_width = 600
    orig_w, orig_h = fountain_frames[0].get_width(), fountain_frames[0].get_height()
    scale_factor = fountain_width / orig_w
    fountain_scaled_frames = [pygame.transform.smoothscale(frame, (fountain_width, int(orig_h * scale_factor))) for frame in fountain_frames]
    fountain_frame_idx = 0
    # Kris
    kris_idle_dir = os.path.join(base_dir, 'sprites', 'spr_krisb_idle')
    kris_idle_files = sorted([os.path.join(kris_idle_dir, f) for f in os.listdir(kris_idle_dir) if f.lower().endswith('.png')])
    kris_base_img = pygame.image.load(kris_idle_files[0]).convert_alpha()
    kris_target_size = (kris_base_img.get_width() * 3, kris_base_img.get_height() * 3)
    kris_idle_frames = [pygame.transform.smoothscale(pygame.image.load(f).convert_alpha(), kris_target_size) for f in kris_idle_files]
    kris_frame_idx = 0
    kris_rect = kris_idle_frames[0].get_rect()
    kris_rect.left = 350
    kris_rect.centery = screen_height // 2 - 100
    # Susie
    susie_idle_dir = os.path.join(base_dir, 'sprites', 'spr_susieb_idle')
    susie_idle_files = sorted([os.path.join(susie_idle_dir, f) for f in os.listdir(susie_idle_dir) if f.lower().endswith('.png')])
    susie_base_img = pygame.image.load(susie_idle_files[0]).convert_alpha()
    susie_target_size = (susie_base_img.get_width() * 3, susie_base_img.get_height() * 3)
    susie_idle_frames = [pygame.transform.smoothscale(pygame.image.load(f).convert_alpha(), susie_target_size) for f in susie_idle_files]
    susie_frame_idx = 0
    susie_rect = susie_idle_frames[0].get_rect()
    susie_rect.left = kris_rect.left - 120
    susie_rect.centery = kris_rect.centery + 100
    # Ralsei
    ralsei_idle_dir = os.path.join(base_dir, 'sprites', 'spr_ralsei_idle')
    ralsei_idle_files = sorted([os.path.join(ralsei_idle_dir, f) for f in os.listdir(ralsei_idle_dir) if f.lower().endswith('.png')])
    ralsei_idle_orig = pygame.image.load(ralsei_idle_files[0]).convert_alpha()
    ralsei_target_size = (int(ralsei_idle_orig.get_width() * 3), int(ralsei_idle_orig.get_height() * 3))
    ralsei_idle_frames = [pygame.transform.smoothscale(pygame.image.load(f).convert_alpha(), ralsei_target_size) for f in ralsei_idle_files]
    ralsei_frame_idx = 0
    ralsei_rect = ralsei_idle_frames[0].get_rect()
    ralsei_rect.left = susie_rect.left - 10
    ralsei_rect.centery = susie_rect.centery + 100
    # Battle box
    battle_box_width = 450
    battle_box_height = 300
    battle_box_border = 4
    battle_box_color = (0, 0, 0)
    battle_box_border_color = (0, 255, 0)
    battle_box_rect = pygame.Rect((screen_width - battle_box_width) // 2 + 50, (screen_height - battle_box_height) // 2 + 20, battle_box_width, battle_box_height)
    # Heart
    heart_size = 32
    heart_img_0 = pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_heart', 'spr_heart_0.png')).convert_alpha()
    heart_img_0 = pygame.transform.smoothscale(heart_img_0, (heart_size, heart_size))
    heart_img_1 = pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_heart', 'spr_heart_1.png')).convert_alpha()
    heart_img_1 = pygame.transform.smoothscale(heart_img_1, (heart_size, heart_size))
    # Knight idle
    knight_idle_img = pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_roaringknight_idle.png')).convert_alpha()
    knight_idle_img = pygame.transform.smoothscale(knight_idle_img, (int(knight_idle_img.get_width() * 3), int(knight_idle_img.get_height() * 3)))
    # Player
    player_x = battle_box_rect.left + battle_box_width // 2 - heart_size // 2
    player_y = battle_box_rect.top + battle_box_height // 2 - heart_size // 2
    player_lives = 99
    font = pygame.font.SysFont(None, 48)
    clock = pygame.time.Clock()
    invincible = False
    show_knight_idle = True
    knight_trail = []
    trail_length = 10
    trail_alphas = [80, 70, 60, 50, 40, 30, 20, 15, 10, 5]
    player_speed = 5
    # For attacks that need PreAttack1
    knight_point_img = knight_idle_img
    knight_point_rect = knight_idle_img.get_rect()
    knight_point_frames = [knight_idle_img]
    triangle_knight_img = knight_idle_img
    triangle_knight_rect = knight_idle_img.get_rect()
    triangle_start_time = pygame.time.get_ticks()
    knight_reverse_duration = 500
    invincible_until = 0
    # For Attacks 1, 6
    knight_point_trail = []
    # For Attack 2,8
    base_dir = base_dir
    # For Attacks 3,7
    # For Attacks 5,9,10
    # Now, select and return the attack instance
    if attack_name == 'Attack1':
        return Attack1(screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
            kris_idle_frames, kris_frame_idx, kris_rect,
            susie_idle_frames, susie_frame_idx, susie_rect,
            ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
            battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives,
            knight_point_img, knight_point_rect, knight_point_frames,
            clock, player_speed,
            screen_height, base_dir, knight_point_trail,
            16, 4, 8, len(kris_idle_frames), 8, len(susie_idle_frames), 8, len(ralsei_idle_frames),
            0, 0, 0, 0, invincible_until, triangle_start_time, triangle_knight_img, triangle_knight_rect, knight_reverse_duration, knight_idle_img)
    elif attack_name == 'Attack2':
        return Attack2(screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
            kris_idle_frames, kris_frame_idx, kris_rect,
            susie_idle_frames, susie_frame_idx, susie_rect,
            ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
            battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives,
            clock, player_speed, base_dir, knight_idle_img)
    elif attack_name == 'Attack3':
        return Attack3(screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
            kris_idle_frames, kris_frame_idx, kris_rect,
            susie_idle_frames, susie_frame_idx, susie_rect,
            ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
            battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
            knight_idle_img, show_knight_idle, clock,
            knight_trail, trail_length, trail_alphas)
    elif attack_name == 'Attack4':
        return Attack4(screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
            kris_idle_frames, kris_frame_idx, kris_rect,
            susie_idle_frames, susie_frame_idx, susie_rect,
            ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
            battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
            knight_idle_img, show_knight_idle, clock,
            base_dir=base_dir, player_speed=player_speed)
    elif attack_name == 'Attack5':
        return Attack5(screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
            kris_idle_frames, kris_frame_idx, kris_rect,
            susie_idle_frames, susie_frame_idx, susie_rect,
            ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
            battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
            knight_idle_img, show_knight_idle, clock,
            base_dir=base_dir, player_speed=player_speed)
    elif attack_name == 'Attack6':
        return Attack1(screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
            kris_idle_frames, kris_frame_idx, kris_rect,
            susie_idle_frames, susie_frame_idx, susie_rect,
            ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
            battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives,
            knight_point_img, knight_point_rect, knight_point_frames,
            clock, player_speed,
            screen_height, base_dir, knight_point_trail,
            16, 4, 8, len(kris_idle_frames), 8, len(susie_idle_frames), 8, len(ralsei_idle_frames),
            0, 0, 0, 0, invincible_until, triangle_start_time, triangle_knight_img, triangle_knight_rect, knight_reverse_duration, knight_idle_img, starchild_scale=1.2)
    elif attack_name == 'Attack7':
        return Attack7(screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
            kris_idle_frames, kris_frame_idx, kris_rect,
            susie_idle_frames, susie_frame_idx, susie_rect,
            ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
            battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
            knight_idle_img, show_knight_idle, clock,
            knight_trail, trail_length, trail_alphas)
    elif attack_name == 'Attack8':
        return Attack8(screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
            kris_idle_frames, kris_frame_idx, kris_rect,
            susie_idle_frames, susie_frame_idx, susie_rect,
            ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
            battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives,
            clock, 5, base_dir, knight_idle_img, show_wheel=True)
    elif attack_name == 'Attack9':
        return Attack5(screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
            kris_idle_frames, kris_frame_idx, kris_rect,
            susie_idle_frames, susie_frame_idx, susie_rect,
            ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
            battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
            knight_idle_img, show_knight_idle, clock,
            base_dir=base_dir, player_speed=player_speed,
            sequences=[('spr_rk_spinslash4_red.png', 'spr_rk_spinslash4.png')]*5)
    elif attack_name == 'Attack10':
        return Attack10(screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
            kris_idle_frames, kris_frame_idx, kris_rect,
            susie_idle_frames, susie_frame_idx, susie_rect,
            ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
            battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
            knight_idle_img, show_knight_idle, clock,
            base_dir=base_dir, player_speed=player_speed)
    elif attack_name == 'Final':
        return FinalAttackSequence(screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
            kris_idle_frames, kris_frame_idx, kris_rect,
            susie_idle_frames, susie_frame_idx, susie_rect,
            ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
            battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, invincible,
            knight_idle_img, show_knight_idle, clock,
            base_dir=base_dir)
    else:
        raise ValueError(f"Unknown attack name: {attack_name}")


if __name__ == "__main__":
    main()


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
    triangle_knight_img, triangle_knight_rect, triangle_start_time, \
    knight_reverse_duration, knight_idle_img = PreAttack1(
        screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
        kris_rect, battle_box_rect, knight_idle_img, clock,
        battle_box_color, battle_box_border_color, battle_box_border,
        heart_img_0, player_x, player_y, heart_size,
        kris_idle_frames, kris_frame_idx, kris_rect,
        susie_idle_frames, susie_frame_idx, susie_rect,
        ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
        player_speed=player_speed
    )

    # Start Attack 1 (call Attack1 with all required arguments)
    Attack1(
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
    Attack2(
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
        ralsei_anim_speed=8, ralsei_frame_count=None
    )

    pygame.quit()
    sys.exit()

def play_battle_intro(screen, bg_img, fountain_scaled_frames, fountain_frame_idx, kris_idle_frames, kris_rect, susie_idle_frames, susie_rect, ralsei_idle_frames, ralsei_rect, battle_box_rect, base_dir, kris_target_size, susie_target_size, ralsei_target_size, kris_frame_idx, susie_frame_idx, ralsei_frame_idx, battle_box_color, battle_box_border_color, battle_box_border, heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, fountain_anim_speed, fountain_frame_count, kris_anim_speed, kris_frame_count, susie_anim_speed, susie_frame_count, ralsei_anim_speed, ralsei_frame_count, fountain_anim_timer, kris_anim_timer, susie_anim_timer, ralsei_anim_timer):
    import time
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

# Rename the current Attack1 to PreAttack1
def PreAttack1(
    screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
    kris_rect, battle_box_rect, knight_idle_img, clock,
    battle_box_color, battle_box_border_color, battle_box_border,
    heart_img_0, player_x, player_y, heart_size,
    kris_idle_frames, kris_frame_idx, kris_rect_in, susie_idle_frames, susie_frame_idx, susie_rect_in,
    ralsei_idle_frames, ralsei_frame_idx, ralsei_rect_in,
    player_speed=5
):
    global knight_trail, trail_length, trail_alphas
    # Input lockout for 200ms to prevent accidental movement from held keys
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
        # Draw everything
        bg_img_scaled = pygame.transform.scale(bg_img, (screen.get_width(), screen.get_height()))
        screen.blit(bg_img_scaled, (0, 0))
        # Draw battle box
        pygame.draw.rect(screen, battle_box_color, battle_box_rect)
        pygame.draw.rect(screen, battle_box_border_color, battle_box_rect, battle_box_border)
        # Draw player heart
        screen.blit(heart_img_0, (player_x, player_y))
        # Draw heroes
        screen.blit(kris_idle_frames[kris_frame_idx], kris_rect_in)
        screen.blit(susie_idle_frames[susie_frame_idx], susie_rect_in)
        screen.blit(ralsei_idle_frames[ralsei_frame_idx], ralsei_rect_in)
        # Draw trail
        for i, (img, rect) in enumerate(reversed(knight_trail)):
            img = img.copy()
            img.set_alpha(trail_alphas[i])
            rect = rect.copy()
            rect.left += 40 + i * 10
            screen.blit(img, rect)
        # Draw Knight
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
        screen.blit(kris_idle_frames[kris_frame_idx], kris_rect_in)
        screen.blit(susie_idle_frames[susie_frame_idx], susie_rect_in)
        screen.blit(ralsei_idle_frames[ralsei_frame_idx], ralsei_rect_in)
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

    return knight_point_frames[-1], knight_rect, knight_point_frames, player_x, player_y, triangle_knight_img, triangle_knight_rect, triangle_start_time, knight_reverse_duration, knight_idle_img

# Move the triangle, star, and starchild attack logic from main() into a new function called Attack1
def Attack1(
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
):
    global knight_trail, trail_length, trail_alphas
     # Use a single attack_phase variable to control Knight state
    attack_phase = 'triangle'  # 'triangle', 'reverse', 'idle'
    triangle_active = True
    triangle_start_time = pygame.time.get_ticks()
    triangle_knight_img = knight_point_img.copy()
    triangle_knight_rect = knight_point_rect.copy()
    knight_point_trail.clear()
    knight_point_trail.append((triangle_knight_img.copy(), triangle_knight_rect.copy()))
    knight_reverse_anim = False
    knight_reverse_start = 0
    knight_reverse_duration = 500  # ms (adjust as needed)
    knight_reverse_idx = 0
    knight_reverse_frames = []
    # Timer for when to allow idle
    knight_idle_timer = 0

    # Triangle effect setup (use last pointing frame, not idle)
    triangle_tip = (triangle_knight_rect.left, triangle_knight_rect.centery)
    triangle_bottom = (0, screen_height)
    triangle_top = (0, -50)
    triangle_points = [triangle_tip, triangle_bottom, triangle_top]
    xs = [p[0] for p in triangle_points]
    ys = [p[1] for p in triangle_points]
    triangle_min_x, triangle_max_x = min(xs), max(xs)
    triangle_min_y, triangle_max_y = min(ys), max(ys)
    triangle_width = triangle_max_x - triangle_min_x
    triangle_height = triangle_max_y - triangle_min_y
    # Create fill surface
    flow0 = pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_knight_purple_star_flow', 'spr_knight_bullet_flow_0.png')).convert_alpha()
    flow0.set_alpha(150)
    stretched_img = pygame.transform.smoothscale(flow0, (triangle_width, triangle_height))
    fill_surf = pygame.Surface((triangle_width, triangle_height), pygame.SRCALPHA)
    fill_surf.blit(stretched_img, (0, 0))
    mask_surf = pygame.Surface((triangle_width, triangle_height), pygame.SRCALPHA)
    tri_points = [(x - triangle_min_x, y - triangle_min_y) for (x, y) in triangle_points]
    pygame.draw.polygon(mask_surf, (255, 255, 255, 255), tri_points)
    fill_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    triangle_fill_surf = fill_surf
    # Play sound
    sfx_path = os.path.join(base_dir, 'sprites', 'sound_effects', 'purple_blast.wav')
    sfx = pygame.mixer.Sound(sfx_path)
    sfx.set_volume(1.0)
    sfx.play(fade_ms=0)

    # Add these variables before the main loop
    triangle_timer = 0
    triangle_duration = 1200  # ms
    triangle_hold = 500  # ms
    attack_end_time = 0

    knight_idle_allowed = False  # Only allow idle after attack sequence
    idle_redraw_once = False

    # For moving bullet and sliding battle box
    bullet1_img_orig = pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_knight_purple_star_flow', 'spr_knight_bullet_flow_1.png')).convert_alpha()
    bullet1_scale = 2.5
    bullet1_img = pygame.transform.smoothscale(
        bullet1_img_orig,
        (int(bullet1_img_orig.get_width() * bullet1_scale), int(bullet1_img_orig.get_height() * bullet1_scale))
    )
    bullet1_img.set_alpha(180)
    battle_box_slide_px = 90
    battle_box_slide_duration = 3000  # ms
    battle_box_slide_start = battle_box_rect.left

    # For star bullets
    star_bullet_img = pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_knight_bullet_star', 'spr_knight_bullet_star_0.png')).convert_alpha()
    star_bullet_img = pygame.transform.smoothscale(star_bullet_img, (int(star_bullet_img.get_width() * 1.5), int(star_bullet_img.get_height() * 1.5)))
    star_bullets = []  # Each bullet: {'x': float, 'y': float, 'vx': float, 'vy': float, 'spawn_time': float, 'active': bool}
    star_bullets_spawned = False
    star_bullet_base_speed = 700  # Even faster base speed
    star_bullet_duration = 3000  # ms (fly until triangle is over)
    num_star_bullets = 25
    star_attack_sfx = pygame.mixer.Sound(os.path.join(base_dir, 'sprites', 'sound_effects', 'star_attack.wav'))

    # Add a phase for star bullet reversal
    star_reverse_duration = 1000  # ms
    star_reverse_start = 0

    # Load star bullet animation frames
    star_bullet_img_0 = star_bullet_img
    star_bullet_img_1 = pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_knight_bullet_star', 'spr_knight_bullet_star_1.png')).convert_alpha()
    star_bullet_img_1 = pygame.transform.smoothscale(star_bullet_img_1, (int(star_bullet_img_1.get_width() * 1.5), int(star_bullet_img_1.get_height() * 1.5)))
    star_bullet_img_2 = pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_knight_bullet_star', 'spr_knight_bullet_star_2.png')).convert_alpha()
    star_bullet_img_2 = pygame.transform.smoothscale(star_bullet_img_2, (int(star_bullet_img_2.get_width() * 1.5), int(star_bullet_img_2.get_height() * 1.5)))
    # Load starchild projectiles (up and down)
    starchild_img_up = pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_knight_starchild', 'spr_knight_starchild_up.png')).convert_alpha()
    starchild_img_up = pygame.transform.smoothscale(starchild_img_up, (int(starchild_img_up.get_width() * 1.2), int(starchild_img_up.get_height() * 1.2)))
    starchild_img_down = pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_knight_starchild', 'spr_knight_starchild_down.png')).convert_alpha()
    starchild_img_down = pygame.transform.smoothscale(starchild_img_down, (int(starchild_img_down.get_width() * 1.2), int(starchild_img_down.get_height() * 1.2)))
    starchilds = []  # Each: {'x': float, 'y': float, 'vx': float, 'vy': float, 'spawn_time': float}
    starchilds_spawned = False
    starchild_speed = 160
    starchild_delay_early = 0
    starchild_delay_late = 120  # ms delay for late group

    # Add a flag to trigger starchild explosion only after star_reverse phase is fully complete
    starchilds_pending_explosion = False
    starchilds_exploded = False
    starchilds_display_start = None

    screen_rect = screen.get_rect()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        # Draw background
        bg_img_scaled = pygame.transform.scale(bg_img, (screen.get_width(), screen.get_height()))
        screen.blit(bg_img_scaled, (0, 0))

        # Draw Kris's idle animation (define kris_rect first)
        kris_img = kris_idle_frames[kris_frame_idx]
        kris_rect = kris_img.get_rect()
        kris_rect.left = 350  # 350px from left
        kris_rect.centery = screen_height // 2 - 100  
        screen.blit(kris_img, kris_rect)

        # Draw fountain animation (cycling 4 frames), now kris_rect is defined
        fountain_img = fountain_scaled_frames[fountain_frame_idx]
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
        screen.blit(fountain_img, fountain_rect)

        # Draw Susie's idle animation
        susie_img = susie_idle_frames[susie_frame_idx]
        susie_rect = susie_img.get_rect()
        susie_rect.left = kris_rect.left - 120
        susie_rect.centery = kris_rect.centery + 100  # 100px below Kris
        screen.blit(susie_img, susie_rect)

        # Draw Ralsei's idle animation
        ralsei_img = ralsei_idle_frames[ralsei_frame_idx]
        ralsei_rect = ralsei_img.get_rect()
        ralsei_rect.left = susie_rect.left - 10  # 30px to the left of Susie
        ralsei_rect.centery = susie_rect.centery + 100  # 100px below Susie
        screen.blit(ralsei_img, ralsei_rect)

        # Draw battle box (black square with green border)
        pygame.draw.rect(screen, battle_box_color, battle_box_rect)
        pygame.draw.rect(screen, battle_box_border_color, battle_box_rect, battle_box_border)

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

        # Collision detection for star bullets and starchilds
        player_rect = pygame.Rect(player_x, player_y, heart_size, heart_size)
        player_center = (player_x + heart_size // 2, player_y + heart_size // 2)
        hit_this_frame = False
        # Star bullets (during triangle, reverse, star_reverse)
        if attack_phase in ('triangle', 'reverse', 'star_reverse'):
            for bullet in star_bullets:
                if bullet.get('x') is not None and bullet.get('y') is not None:
                    r = star_bullet_img_0.get_width() // 3
                    dx = bullet['x'] - player_center[0]
                    dy = bullet['y'] - player_center[1]
                    if dx * dx + dy * dy < r * r:
                        hit_this_frame = True
                        break
        # Starchilds (after explosion)
        for sc in starchilds:
            if now >= sc['spawn_time']:
                sc['x'] += sc['vx'] / 60.0
                sc['y'] += sc['vy'] / 60.0
                # Select the correct image and rotation
                if sc['img'] == 'up':
                    base_img = starchild_img_up
                else:
                    base_img = starchild_img_down
                rotated_img = pygame.transform.rotate(base_img, sc['angle'])
                rect = rotated_img.get_rect(center=(int(sc['x']), int(sc['y'])))
                if screen_rect.colliderect(rect):
                    screen.blit(rotated_img, rect)
                # Use full rect for hitbox
                if rect.collidepoint(player_center):
                    hit_this_frame = True
                    break
        # Invincibility logic
        if pygame.time.get_ticks() < invincible_until:
            invincible = True
        else:
            invincible = False
        if hit_this_frame and not invincible:
            player_lives = max(0, player_lives - 1)
            invincible_until = pygame.time.get_ticks() + 1000  # 1 second invincibility
            invincible = True

        # Draw lives counter
        lives_surf = font.render(f"LIVES: {player_lives}", True, (255, 255, 255))
        screen.blit(lives_surf, (50, 50))

        # Draw player heart (flashing if invincible)
        if invincible:
            # Alternate every 100ms
            if ((pygame.time.get_ticks() // 100) % 2) == 0:
                heart_draw_img = heart_img_0
            else:
                heart_draw_img = heart_img_1
        else:
            heart_draw_img = heart_img_0
        screen.blit(heart_draw_img, (player_x, player_y))

        # Draw the Knight and its trail depending on attack_phase
        if attack_phase == 'triangle':
            now = pygame.time.get_ticks()
            elapsed = now - triangle_start_time
            # Slide the battle box left over 3 seconds
            slide_offset = int(battle_box_slide_px * min(elapsed / battle_box_slide_duration, 1.0))
            battle_box_rect.left = battle_box_slide_start - slide_offset
            # Redraw the triangle points and fill to match the new box position
            # Do NOT move the Knight with the battle box
            # triangle_knight_rect.left and centery remain fixed
            triangle_tip = (triangle_knight_rect.left, triangle_knight_rect.centery)
            triangle_points = [triangle_tip, triangle_bottom, triangle_top]
            xs = [p[0] for p in triangle_points]
            ys = [p[1] for p in triangle_points]
            triangle_min_x, triangle_max_x = min(xs), max(xs)
            triangle_min_y, triangle_max_y = min(ys), max(ys)
            triangle_width = triangle_max_x - triangle_min_x
            triangle_height = triangle_max_y - triangle_min_y
            # Recreate fill surface for the triangle
            stretched_img = pygame.transform.smoothscale(flow0, (triangle_width, triangle_height))
            fill_surf = pygame.Surface((triangle_width, triangle_height), pygame.SRCALPHA)
            fill_surf.blit(stretched_img, (0, 0))
            mask_surf = pygame.Surface((triangle_width, triangle_height), pygame.SRCALPHA)
            tri_points = [(x - triangle_min_x, y - triangle_min_y) for (x, y) in triangle_points]
            pygame.draw.polygon(mask_surf, (255, 255, 255, 255), tri_points)
            fill_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            triangle_fill_surf = fill_surf
            # Draw the filled triangle
            screen.blit(triangle_fill_surf, (triangle_min_x, triangle_min_y))
            # Animate bullet1 starting 10px to the left of the Knight's tip and moving left at 2x speed
            bullet1_start_x = triangle_tip[0] - bullet1_img.get_width() // 2 - 10
            bullet1_end_x = -bullet1_img.get_width()  # Move out of bounds to the left
            bullet1_progress = min(elapsed / 1500, 1.0)  # 1.5 seconds for 2x speed
            bullet1_x = int(bullet1_start_x + (bullet1_end_x - bullet1_start_x) * bullet1_progress)
            # Place bullet lower, closer to the vertical center of the triangle (e.g., 0.55 from tip to bottom)
            bullet1_y = int(triangle_tip[1] + (triangle_bottom[1] - triangle_tip[1]) * 0.55)
            screen.blit(bullet1_img, (bullet1_x, bullet1_y - bullet1_img.get_height() // 2))

            # Spawn star bullets with random delays and play sound for each
            if not star_bullets_spawned:
                star_bullets.clear()
                spawn_times = sorted([random.uniform(0, 3000) for _ in range(num_star_bullets)])
                for st in spawn_times:
                    target_x = -50
                    target_y = random.uniform(-100, screen_height + 100)
                    dx = target_x - triangle_tip[0]
                    dy = target_y - triangle_tip[1]
                    speed_factor = random.uniform(1, 1.75)
                    duration = star_bullet_duration / 1000.0 / speed_factor
                    vx = dx / duration
                    vy = dy / duration
                    star_bullets.append({'x': triangle_tip[0], 'y': triangle_tip[1], 'vx': vx, 'vy': vy, 'spawn_time': st, 'active': False})
                star_bullets_spawned = True
                star_bullet_start_time = now
            # Update and draw star bullets
            for bullet in star_bullets:
                t = now - star_bullet_start_time
                if not bullet['active'] and t >= bullet['spawn_time']:
                    bullet['active'] = True
                    # Play sound for each star spawn
                    star_attack_sfx.play()
                    bullet['start_x'] = triangle_tip[0]
                    bullet['start_y'] = triangle_tip[1]
                if bullet['active']:
                    dt = t - bullet['spawn_time']
                    if dt < star_bullet_duration:
                        bullet['x'] = bullet['start_x'] + bullet['vx'] * (dt / 1000.0)
                        bullet['y'] = bullet['start_y'] + bullet['vy'] * (dt / 1000.0)
                        # Only draw the default star bullet sprite during the forward phase
                        screen.blit(star_bullet_img_0, (int(bullet['x'] - star_bullet_img_0.get_width() // 2), int(bullet['y'] - star_bullet_img_0.get_height() // 2)))
            # Update and draw the trail for the pointing Knight
            knight_point_trail.insert(0, (triangle_knight_img.copy(), triangle_knight_rect.copy()))
            if len(knight_point_trail) > trail_length:
                knight_point_trail.pop()
            for i, (img, rect) in enumerate(reversed(knight_point_trail)):
                img = img.copy()
                img.set_alpha(trail_alphas[i])
                rect = rect.copy()
                rect.left += 40 + i * 10
                screen.blit(img, rect)
            # Draw the Knight sprite (pointing frame)
            screen.blit(triangle_knight_img, triangle_knight_rect)
            if elapsed > 3000:  # 3 seconds for triangle phase
                attack_phase = 'reverse'
                knight_reverse_start = pygame.time.get_ticks()
                knight_reverse_frames = list(reversed(knight_point_frames))
                knight_reverse_idx = 0
                # Prepare for star reversal
                for bullet in star_bullets:
                    bullet['orig_vx'] = bullet['vx']
                    bullet['orig_vy'] = bullet['vy']
                    bullet['reverse_x'] = bullet['x']
                    bullet['reverse_y'] = bullet['y']
                star_reverse_start = 0
        elif attack_phase == 'reverse':
            now = pygame.time.get_ticks()
            reverse_elapsed = now - knight_reverse_start
            frame_time = knight_reverse_duration / max(1, len(knight_reverse_frames))
            knight_reverse_idx = min(int(reverse_elapsed // frame_time), len(knight_reverse_frames) - 1)
            knight_img = knight_reverse_frames[knight_reverse_idx]
            knight_rect = knight_img.get_rect()
            knight_rect.left = triangle_knight_rect.left
            knight_rect.centery = triangle_knight_rect.centery
            # Update and draw the trail for the reverse animation
            knight_point_trail.insert(0, (knight_img.copy(), knight_rect.copy()))
            if len(knight_point_trail) > trail_length:
                knight_point_trail.pop()
            for i, (img, rect) in enumerate(reversed(knight_point_trail)):
                img = img.copy()
                img.set_alpha(trail_alphas[i])
                rect = rect.copy()
                rect.left += 40 + i * 10
                screen.blit(img, rect)
            screen.blit(knight_img, knight_rect)
            # Draw the star bullets at their last position from the triangle phase
            for bullet in star_bullets:
                if bullet.get('x') is not None and bullet.get('y') is not None:
                    # Only draw the default star bullet sprite during the reverse phase
                    screen.blit(star_bullet_img_0, (int(bullet['x'] - star_bullet_img_0.get_width() // 2), int(bullet['y'] - star_bullet_img_0.get_height() // 2)))
            if knight_reverse_idx == len(knight_reverse_frames) - 1:
                attack_phase = 'star_reverse'
                star_reverse_start = pygame.time.get_ticks()
                for bullet in star_bullets:
                    bullet['vx'] = -bullet['orig_vx']
                    bullet['vy'] = -bullet['orig_vy']
                    bullet['x'] = bullet['reverse_x']
                    bullet['y'] = bullet['reverse_y']
                    bullet['spawn_time'] = star_reverse_start
                knight_idle_timer = pygame.time.get_ticks()
        elif attack_phase == 'star_reverse':
            now = pygame.time.get_ticks()
            reverse_elapsed = now - star_reverse_start
            for bullet in star_bullets:
                if bullet.get('vx') is not None:
                    # Use reverse_elapsed for all bullets in this phase
                    dt = min(reverse_elapsed, star_reverse_duration)
                    bullet['x'] = bullet['reverse_x'] + bullet['vx'] * (dt / 1000.0)
                    bullet['y'] = bullet['reverse_y'] + bullet['vy'] * (dt / 1000.0)
                    # Animate star bullet: 0 -> 1 -> 2 only during the backward phase
                    star_anim_img = star_bullet_img_0
                    if dt > star_reverse_duration * 0.33:
                        star_anim_img = star_bullet_img_1
                    if dt > star_reverse_duration * 0.66:
                        star_anim_img = star_bullet_img_2
                    screen.blit(star_anim_img, (int(bullet['x'] - star_anim_img.get_width() // 2), int(bullet['y'] - star_anim_img.get_height() // 2)))
            # Draw starchilds
            for sc in starchilds:
                if now >= sc['spawn_time']:
                    sc['x'] += sc['vx'] / 60.0
                    sc['y'] += sc['vy'] / 60.0
                    # Select the correct image and rotation
                    if sc['img'] == 'up':
                        base_img = starchild_img_up
                    else:
                        base_img = starchild_img_down
                    rotated_img = pygame.transform.rotate(base_img, sc['angle'])
                    rect = rotated_img.get_rect(center=(int(sc['x']), int(sc['y'])))
                    if screen_rect.colliderect(rect):
                        screen.blit(rotated_img, rect)
                    # Use full rect for hitbox
                    if rect.collidepoint(player_center):
                        hit_this_frame = True
                        break
            if reverse_elapsed >= star_reverse_duration and not starchilds_exploded:
                # Only trigger starchild explosion once, after both phases are done
                for bullet in star_bullets:
                    if not bullet.get('exploded'):
                        bullet['exploded'] = True
                        scx, scy = bullet['x'], bullet['y']
                        now_spawn = now
                        # Early group: up, down-right (down -45°), down-left (down +45°)
                        # up
                        starchilds.append({'x': scx, 'y': scy, 'vx': 0, 'vy': -starchild_speed, 'spawn_time': now_spawn + starchild_delay_early, 'img': 'up', 'angle': 0})
                        # down-right (down -45°)
                        angle = 45
                        vx = starchild_speed * math.sin(math.radians(45))
                        vy = starchild_speed * math.cos(math.radians(45))
                        starchilds.append({'x': scx, 'y': scy, 'vx': vx, 'vy': vy, 'spawn_time': now_spawn + starchild_delay_early, 'img': 'down', 'angle': angle})
                        # down-left (down +45°)
                        angle = -45
                        vx = -starchild_speed * math.sin(math.radians(45))
                        vy = starchild_speed * math.cos(math.radians(45))
                        starchilds.append({'x': scx, 'y': scy, 'vx': vx, 'vy': vy, 'spawn_time': now_spawn + starchild_delay_early, 'img': 'down', 'angle': angle})
                        # Late group: down, up-right (up +45°), up-left (up -45°)
                        # down
                        starchilds.append({'x': scx, 'y': scy, 'vx': 0, 'vy': starchild_speed, 'spawn_time': now_spawn + starchild_delay_late, 'img': 'down', 'angle': 0})
                        # up-right (up +45°)
                        angle = -45
                        vx = starchild_speed * math.sin(math.radians(45))
                        vy = -starchild_speed * math.cos(math.radians(45))
                        starchilds.append({'x': scx, 'y': scy, 'vx': vx, 'vy': vy, 'spawn_time': now_spawn + starchild_delay_late, 'img': 'up', 'angle': angle})
                        # up-left (up -45°)
                        angle = 45
                        vx = -starchild_speed * math.sin(math.radians(45))
                        vy = -starchild_speed * math.cos(math.radians(45))
                        starchilds.append({'x': scx, 'y': scy, 'vx': vx, 'vy': vy, 'spawn_time': now_spawn + starchild_delay_late, 'img': 'up', 'angle': angle})
                starchilds_exploded = True
                star_bullets.clear()
                starchilds_display_start = now
            # After explosion, display starchilds for 1 second before switching to idle
            if starchilds_exploded and starchilds_display_start is not None:
                if now - starchilds_display_start > 1000:
                    # Clear starchilds before switching to idle, before any drawing
                    starchilds.clear()
                    attack_phase = 'idle'
        elif attack_phase == 'idle':
            knight_idle_allowed = True
            if not idle_redraw_once:
                draw_main_scene(
                    screen, bg_img, fountain_scaled_frames, fountain_frame_idx,
                    kris_idle_frames, kris_frame_idx, kris_rect,
                    susie_idle_frames, susie_frame_idx, susie_rect,
                    ralsei_idle_frames, ralsei_frame_idx, ralsei_rect,
                    battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
                    heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, False
                )
                pygame.display.flip()
                idle_redraw_once = True
        if knight_idle_allowed:
            # Only draw the idle Knight and its trail if attack_phase == 'idle'
            float_offset = int(20 * math.sin(pygame.time.get_ticks() / 267))
            knight_idle_rect = knight_idle_img.get_rect()
            knight_idle_rect.centery = kris_rect.centery + 20  # 20px lower than Kris
            knight_idle_rect.left = battle_box_rect.right + 40
            knight_idle_rect.top += float_offset
            trail_img = knight_idle_img.copy()
            trail_img.set_alpha(50)  # Adjust for desired faintness
            trail_rect = knight_idle_rect.copy()
            trail_rect.left += 40  # Adjust offset as desired
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
                rect.left += 40 + i * 10  # Each copy further to the right for a wave effect
                screen.blit(img, rect)

            # Draw the main Knight sprite LAST
            screen.blit(knight_idle_img, knight_idle_rect)

        pygame.display.flip()

        # Advance fountain frame
        fountain_anim_timer += 1
        if fountain_anim_timer >= fountain_anim_speed:
            fountain_frame_idx = (fountain_frame_idx + 1) % fountain_frame_count
            fountain_anim_timer = 0

        # Advance Kris idle frame
        kris_anim_timer += 1
        if kris_anim_timer >= kris_anim_speed:
            kris_frame_idx = (kris_frame_idx + 1) % kris_frame_count
            kris_anim_timer = 0

        # Advance Susie idle frame
        susie_anim_timer += 1
        if susie_anim_timer >= susie_anim_speed:
            susie_frame_idx = (susie_frame_idx + 1) % susie_frame_count
            susie_anim_timer = 0

        # Advance Ralsei idle frame
        ralsei_anim_timer += 1
        if ralsei_anim_timer >= ralsei_anim_speed:
            ralsei_frame_idx = (ralsei_frame_idx + 1) % ralsei_frame_count
            ralsei_anim_timer = 0

        clock.tick(60)  # 60 FPS

        # If the attack phase is 'idle' and the idle redraw has happened, end the loop
        if attack_phase == 'idle' and idle_redraw_once:
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
    # We'll keep the player moving as in idle
    while running:
        now = pygame.time.get_ticks()
        t = min((now - start_time) / anim_duration, 1.0)
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
        pygame.mixer.music.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'black_knife.ogg'))
        pygame.mixer.music.play(-1)
        draw_main_scene.music_started = True
    global knight_trail, trail_length, trail_alphas
    # Draw background
    bg_img_scaled = pygame.transform.scale(bg_img, (screen.get_width(), screen.get_height()))
    screen.blit(bg_img_scaled, (0, 0))
    # Draw Kris
    kris_img = kris_idle_frames[kris_frame_idx]
    kris_rect_draw = kris_img.get_rect()
    kris_rect_draw.left = kris_rect.left
    kris_rect_draw.centery = kris_rect.centery
    screen.blit(kris_img, kris_rect_draw)
    # Draw fountain
    fountain_img = fountain_scaled_frames[fountain_frame_idx]
    fountain_rect = fountain_img.get_rect()
    fountain_rect.left = kris_rect_draw.left + kris_rect_draw.width + 100
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

def Attack2(
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
    ralsei_anim_speed=8, ralsei_frame_count=None
):
    
    print('Attack2: entered')
    import math, random
    # Sword data structure
    class Sword:
        def __init__(self, spawn_time, pos, direction):
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
                self.sword_img = sword_imgs['up']
                self.sword_img_red = sword_imgs_red['up']
                self.line_img = slash_img_horiz
                self.pos = list(pos)
            elif direction == 'down':
                self.sword_img = sword_imgs['down']
                self.sword_img_red = sword_imgs_red['down']
                self.line_img = slash_img_horiz
                self.pos = list(pos)
            elif direction == 'left':
                self.sword_img = sword_imgs['left']
                self.sword_img_red = sword_imgs_red['left']
                self.line_img = slash_img_vert
                self.pos = list(pos)
            elif direction == 'right':
                self.sword_img = sword_imgs['right']
                self.sword_img_red = sword_imgs_red['right']
                self.line_img = slash_img_vert
                self.pos = list(pos)
            elif direction == 'downright':
                self.sword_img = pygame.transform.rotate(sword_imgs['right'], -45)
                self.line_img = pygame.transform.rotate(slash_img_horiz, -45)
                self.pos = [0, 0]  # Will be set in update()
            elif direction == 'downleft':
                self.sword_img = pygame.transform.rotate(sword_imgs['left'], 45)
                self.line_img = pygame.transform.rotate(slash_img_horiz, 45)
                self.pos = [0, 0]
            elif direction == 'upleft':
                self.sword_img = pygame.transform.rotate(sword_imgs['left'], -45)
                self.line_img = pygame.transform.rotate(slash_img_horiz, -45)
                self.pos = [0, 0]
            elif direction == 'upright':
                self.sword_img = pygame.transform.rotate(sword_imgs['right'], 45)
                self.line_img = pygame.transform.rotate(slash_img_horiz, 45)
                self.pos = [0, 0]
            self.rect = self.sword_img.get_rect(center=self.pos)
            self.line_rect = self.line_img.get_rect(center=self.pos)
            self.is_corner = direction in ('downright', 'downleft', 'upleft', 'upright')
            self.initialized = False  # Track if we've set the initial position for diagonals
            # Debug print for diagonals
            if direction in ('downright', 'downleft', 'upleft', 'upright'):
                print(f"[DEBUG] Sword spawned: direction={direction}, pos={self.pos}")
        def project_point_on_segment(self, px, py, x1, y1, x2, y2):
            dx, dy = x2 - x1, y2 - y1
            if dx == dy == 0:
                return x1, y1
            t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
            t = max(0, min(1, t))
            return x1 + t * dx, y1 + t * dy
        def update(self, player_center, now, box, border):
            self.timer = (now - self.spawn_time) / 1000.0
            if self.timer < 0.7:
                if self.direction == 'up':
                    self.pos[0] = min(max(player_center[0], box.left + margin), box.right - margin)
                    self.pos[1] = box.bottom + margin
                elif self.direction == 'down':
                    self.pos[0] = min(max(player_center[0], box.left + margin), box.right - margin)
                    self.pos[1] = box.top - margin
                elif self.direction == 'left':
                    self.pos[0] = box.right + margin
                    self.pos[1] = min(max(player_center[1], box.top + margin), box.bottom - margin)
                elif self.direction == 'right':
                    self.pos[0] = box.left - margin
                    self.pos[1] = min(max(player_center[1], box.top + margin), box.bottom - margin)
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
                slash = pygame.transform.scale(slash_img_horiz, (1, length))
                screen.blit(slash, (x, y1))
            elif self.direction == 'down':
                x = int(self.pos[0])
                y0 = box.top
                y1 = box.bottom
                length = abs(y1 - y0)
                slash = pygame.transform.scale(slash_img_horiz, (1, length))
                screen.blit(slash, (x, y0))
            elif self.direction == 'left':
                y = int(self.pos[1])
                x0 = box.right
                x1 = box.left
                length = abs(x1 - x0)
                slash = pygame.transform.scale(slash_img_vert, (length, 1))
                screen.blit(slash, (x1, y))
            elif self.direction == 'right':
                y = int(self.pos[1])
                x0 = box.left
                x1 = box.right
                length = abs(x1 - x0)
                slash = pygame.transform.scale(slash_img_vert, (length, 1))
                screen.blit(slash, (x0, y))
            elif self.direction == 'downright':
                start = (int(self.pos[0]), int(self.pos[1]))
                end = (box.right - border, box.bottom - border)
                pygame.draw.line(screen, (255,0,0), start, end, 3)
                length = int(((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5)
                slash = pygame.transform.scale(self.line_img, (length, int(self.line_img.get_height())))
                angle = -45
                slash = pygame.transform.rotate(slash, angle)
                screen.blit(slash, start)
            elif self.direction == 'downleft':
                start = (int(self.pos[0]), int(self.pos[1]))
                end = (box.left + border, box.bottom - border)
                pygame.draw.line(screen, (255,0,0), start, end, 3)
                length = int(((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5)
                slash = pygame.transform.scale(self.line_img, (length, int(self.line_img.get_height())))
                angle = 45
                slash = pygame.transform.rotate(slash, angle)
                screen.blit(slash, start)
            elif self.direction == 'upleft':
                start = (int(self.pos[0]), int(self.pos[1]))
                end = (box.left + border, box.top + border)
                pygame.draw.line(screen, (255,0,0), start, end, 3)
                length = int(((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5)
                slash = pygame.transform.scale(self.line_img, (length, int(self.line_img.get_height())))
                angle = -45
                slash = pygame.transform.rotate(slash, angle)
                screen.blit(slash, start)
            elif self.direction == 'upright':
                start = (int(self.pos[0]), int(self.pos[1]))
                end = (box.right - border, box.top + border)
                pygame.draw.line(screen, (255,0,0), start, end, 3)
                length = int(((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5)
                slash = pygame.transform.scale(self.line_img, (length, int(self.line_img.get_height())))
                angle = 45
                slash = pygame.transform.rotate(slash, angle)
                screen.blit(slash, start)
    # Load sword sprites
    sword_imgs = {
        'up': pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_knight_sword', 'spr_knight_sword_up.png')).convert_alpha(),
        'down': pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_knight_sword', 'spr_knight_sword_down.png')).convert_alpha(),
        'left': pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_knight_sword', 'spr_knight_sword_left.png')).convert_alpha(),
        'right': pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_knight_sword', 'spr_knight_sword_right.png')).convert_alpha(),
    }
    sword_imgs_red = {
        'up': pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_knight_sword', 'spr_knight_sword_up_red.png')).convert_alpha(),
        'down': pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_knight_sword', 'spr_knight_sword_down_red.png')).convert_alpha(),
        'left': pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_knight_sword', 'spr_knight_sword_left_red.png')).convert_alpha(),
        'right': pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_knight_sword', 'spr_knight_sword_right_red.png')).convert_alpha(),
    }
    # Load sound
    sword_shoot_sfx = pygame.mixer.Sound(os.path.join(base_dir, 'sprites', 'sound_effects', 'sword_shoot.wav'))
    # Load sword slash sprites (vertical and horizontal)
    slash_img_vert = pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_knight_sword_shoot', 'spr_rk_sword_shoot_vert.png')).convert_alpha()
    slash_img_horiz = pygame.image.load(os.path.join(base_dir, 'sprites', 'spr_knight_sword_shoot', 'spr_rk_sword_shoot_horiz.png')).convert_alpha()
    # Make swords larger
    sword_scale = 1.5
    for k in sword_imgs:
        w, h = sword_imgs[k].get_size()
        sword_imgs[k] = pygame.transform.smoothscale(sword_imgs[k], (int(w * sword_scale), int(h * sword_scale)))
        # Also scale the red versions
        w_red, h_red = sword_imgs_red[k].get_size()
        sword_imgs_red[k] = pygame.transform.smoothscale(sword_imgs_red[k], (int(w * sword_scale), int(h * sword_scale)))
    margin = int(0.5 * max(sword_imgs['up'].get_width(), sword_imgs['up'].get_height()))
    box = battle_box_rect
    # Anchor swords to the borders and restrict movement along the border
    positions = [
        (box.left, box.top - margin),            # top-center (moves along top border)
        (box.right + margin, box.top),           # right-center (moves along right border)
        (box.right, box.bottom + margin),        # bottom-center (moves along bottom border)
        (box.left - margin, box.bottom),         # left-center (moves along left border)
        (box.left - margin, box.top - margin),   # top-left (downright)
        (box.right + margin, box.top - margin),  # top-right (downleft)
        (box.right + margin, box.bottom + margin), # bottom-right (upleft)
        (box.left - margin, box.bottom + margin)   # bottom-left (upright)
    ]
    directions = ['up', 'down', 'left', 'right']
    num_swords = 8
    # ... existing code ...
    # Attack2 main loop
    swords = []
    attack_duration = 7000  # ms
    sword_interval = 700  # ms
    start_time = pygame.time.get_ticks()
    next_sword_time = start_time
    sword_idx = 0
    running = True
    invincible_until = 0
    # Animation frame/timer setup
    if kris_frame_count is None:
        kris_frame_count = len(kris_idle_frames)
    if susie_frame_count is None:
        susie_frame_count = len(susie_idle_frames)
    if ralsei_frame_count is None:
        ralsei_frame_count = len(ralsei_idle_frames)
    local_fountain_anim_timer = 0
    local_kris_anim_timer = 0
    local_susie_anim_timer = 0
    local_ralsei_anim_timer = 0
    # Use the incoming frame indices as starting points
    local_fountain_frame_idx = fountain_frame_idx
    local_kris_frame_idx = kris_frame_idx
    local_susie_frame_idx = susie_frame_idx
    local_ralsei_frame_idx = ralsei_frame_idx
    while running:
        now = pygame.time.get_ticks()
        # Advance animation timers and frame indices
        local_fountain_anim_timer += 1
        if local_fountain_anim_timer >= fountain_anim_speed:
            local_fountain_frame_idx = (local_fountain_frame_idx + 1) % fountain_frame_count
            local_fountain_anim_timer = 0
        local_kris_anim_timer += 1
        if local_kris_anim_timer >= kris_anim_speed:
            local_kris_frame_idx = (local_kris_frame_idx + 1) % kris_frame_count
            local_kris_anim_timer = 0
        local_susie_anim_timer += 1
        if local_susie_anim_timer >= susie_anim_speed:
            local_susie_frame_idx = (local_susie_frame_idx + 1) % susie_frame_count
            local_susie_anim_timer = 0
        local_ralsei_anim_timer += 1
        if local_ralsei_anim_timer >= ralsei_anim_speed:
            local_ralsei_frame_idx = (local_ralsei_frame_idx + 1) % ralsei_frame_count
            local_ralsei_anim_timer = 0
        # Spawn swords
        # Prepare a shuffled, non-repeating side list for sword spawns
        if sword_idx == 0:
            spawn_sides = []
            last_side = None
            while len(spawn_sides) < num_swords:
                side = random.choice(directions)
                if side != last_side:
                    spawn_sides.append(side)
                    last_side = side
        if sword_idx < num_swords and now >= next_sword_time:
            side = spawn_sides[sword_idx]
            # Pick a random offset along the side (avoid edges)
            if side == 'up':
                offset = random.randint(30, box.width - 30)
                pos = (box.left + offset, box.top - margin)
            elif side == 'down':
                offset = random.randint(30, box.width - 30)
                pos = (box.left + offset, box.bottom + margin)
            elif side == 'left':
                offset = random.randint(30, box.height - 30)
                pos = (box.left - margin, box.top + offset)
            elif side == 'right':
                offset = random.randint(30, box.height - 30)
                pos = (box.right + margin, box.top + offset)
            swords.append(Sword(now, pos, side))
            sword_idx += 1
            next_sword_time += sword_interval
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
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
        player_rect = pygame.Rect(player_x, player_y, heart_size, heart_size)
        player_center = (player_x + heart_size // 2, player_y + heart_size // 2)
        # Draw everything
        bg_img_scaled = pygame.transform.scale(bg_img, (screen.get_width(), screen.get_height()))
        screen.blit(bg_img_scaled, (0, 0))
        # Draw scene (heroes, box, etc.)
        draw_main_scene(
            screen, bg_img, fountain_scaled_frames, local_fountain_frame_idx,
            kris_idle_frames, local_kris_frame_idx, kris_rect,
            susie_idle_frames, local_susie_frame_idx, susie_rect,
            ralsei_idle_frames, local_ralsei_frame_idx, ralsei_rect,
            battle_box_rect, battle_box_color, battle_box_border_color, battle_box_border,
            heart_img_0, heart_img_1, player_x, player_y, heart_size, font, player_lives, False
        )
        # --- Knight idle animation and trail (added for Attack2) ---
        float_offset = int(20 * math.sin(pygame.time.get_ticks() / 267))
        knight_idle_rect = knight_idle_img.get_rect()
        knight_idle_rect.centery = kris_rect.centery + 20
        knight_idle_rect.left = battle_box_rect.right + 40
        knight_idle_rect.top += float_offset
        trail_img = knight_idle_img.copy()
        trail_img.set_alpha(50)
        trail_rect = knight_idle_rect.copy()
        trail_rect.left += 40
        screen.blit(trail_img, trail_rect)
        knight_trail.insert(0, (knight_idle_img.copy(), knight_idle_rect.copy()))
        if len(knight_trail) > trail_length:
            knight_trail.pop()
        for i, (img, rect) in enumerate(reversed(knight_trail)):
            img = img.copy()
            img.set_alpha(trail_alphas[i])
            rect = rect.copy()
            rect.left += 40 + i * 10
            screen.blit(img, rect)
        screen.blit(knight_idle_img, knight_idle_rect)
        # --- End knight idle animation and trail ---
        # Draw swords and lines
        for sword in swords:
            if sword.timer < 1.0:
                sword.update(player_center, now, box, battle_box_border)
                sword.draw(screen)
                # Play sound and draw line at 0.8s
                if sword.timer >= 0.75 and not sword.sound_played:
                    sword.turn_red()
                    sword_shoot_sfx.play()
                    sword.sound_played = True
                if sword.timer >= 0.9:
                    sword.draw_line(screen, box, battle_box_border)
            else:
                sword.removed = True
        # Remove swords that are done
        swords = [s for s in swords if not s.removed]
        # Collision detection
        hit_this_frame = False
        for sword in swords:
            if sword.rect.colliderect(player_rect):
                hit_this_frame = True
                break
            if sword.timer >= 0.9:
                # Make the slash hitbox larger
                if sword.direction in ('up', 'down'):
                    # Horizontal slash: much taller hitbox
                    slash_hitbox = pygame.Rect(
                        int(sword.pos[0]) - 24, box.top, 48, box.height
                    )
                elif sword.direction in ('left', 'right'):
                    # Vertical slash: much wider hitbox
                    slash_hitbox = pygame.Rect(
                        box.left, int(sword.pos[1]) - 24, box.width, 48
                    )
                else:
                    # Diagonal: use a larger square at the center line
                    slash_hitbox = pygame.Rect(
                        box.left, box.top, box.width, box.height
                    )
                if slash_hitbox.colliderect(player_rect):
                    hit_this_frame = True
                    break
        # Invincibility logic
        if pygame.time.get_ticks() < invincible_until:
            invincible = True
        else:
            invincible = False
        if hit_this_frame and not invincible:
            player_lives = max(0, player_lives - 1)
            invincible_until = pygame.time.get_ticks() + 1000  # 1 second invincibility
            invincible = True
        # Draw lives counter
        lives_surf = font.render(f"LIVES: {player_lives}", True, (255, 255, 255))
        screen.blit(lives_surf, (50, 50))
        # Draw player heart (flashing if invincible)
        if invincible:
            if ((pygame.time.get_ticks() // 100) % 2) == 0:
                heart_draw_img = heart_img_0
            else:
                heart_draw_img = heart_img_1
        else:
            heart_draw_img = heart_img_0
        screen.blit(heart_draw_img, (player_x, player_y))
        pygame.display.flip()
        clock.tick(60)
        # End condition
        if now - start_time > attack_duration and not swords:
            running = False

        # Draw debug circles at the intended corners
        corners = [
            (box.left + battle_box_border, box.top + battle_box_border),
            (box.right - battle_box_border, box.top + battle_box_border),
            (box.right - battle_box_border, box.bottom - battle_box_border),
            (box.left + battle_box_border, box.bottom - battle_box_border),
        ]
        for c in corners:
            pygame.draw.circle(screen, (0,255,0), (int(c[0]), int(c[1])), 8)

if __name__ == "__main__":
    main()

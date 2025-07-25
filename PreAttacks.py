import pygame
import os
import sys
import numpy as np
from PIL import Image
import math
import random

knight_trail = []
trail_length = 10
trail_alphas = [80, 70, 60, 50, 40, 30, 20, 15, 10, 5]

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
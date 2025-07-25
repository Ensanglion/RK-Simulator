import pygame
import os
import sys
import numpy as np
from PIL import Image
import math
import random
from classes import *
from PreAttacks import *

global music_started
music_started = False
knight_trail = []
trail_length = 10
trail_alphas = [80, 70, 60, 50, 40, 30, 20, 15, 10, 5]

OUTLINE_COLOR = (39, 41, 63, 255)  # RGBA for outline

def full_game():
    pygame.init()
    pygame.mixer.init()

    # Get user's screen size
    info = pygame.display.Info()
    screen_width, screen_height = info.current_w, info.current_h
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
    pygame.display.set_caption("IT'S THE KNIGHT!!!")

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

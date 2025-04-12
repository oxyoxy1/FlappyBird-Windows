import pygame
import random
import sys
import time
import os
import json

# Initialize pygame
pygame.init()
pygame.font.init()
clock = pygame.time.Clock()

# Game constants
WIDTH, HEIGHT = 400, 600
GRAVITY = 0.5
FLAP_POWER = -10
PIPE_WIDTH = 70
BASE_PIPE_GAP = 150  # Both visual and hitbox gap
PIPE_FREQ = 1500
FPS = 60
SCORE_FILE = "Contents/scores.json"
DEATH_COOLDOWN = 1275

# Setup display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flappy Bird")

# Hitbox adjustments
BIRD_HITBOX_WIDTH = 24
BIRD_HITBOX_HEIGHT = 20
PIPE_HITBOX_WIDTH = 60  # Slightly narrower than visual pipe width

# Try to load window icon
try:
    icon = pygame.image.load("Contents/icon.ico")
    pygame.display.set_icon(icon)
except:
    pass

# Font setup
font = pygame.font.SysFont("Arial", 36)
score_font = pygame.font.SysFont("Arial", 24)

# Load sounds
SFX_PATH = "Contents/SFX/"
try:
    sfx_hit = pygame.mixer.Sound(SFX_PATH + "hit.wav")
    sfx_die = pygame.mixer.Sound(SFX_PATH + "die.wav")
    sfx_point = pygame.mixer.Sound(SFX_PATH + "point.wav")
    sfx_button = pygame.mixer.Sound(SFX_PATH + "button.wav")
    sfx_wing = pygame.mixer.Sound(SFX_PATH + "wing.wav")
except:
    # Create silent sounds if loading fails
    sfx_hit = sfx_die = sfx_point = sfx_button = sfx_wing = pygame.mixer.Sound(None)

# Load sprites
SPRITE_PATH = "Contents/Sprites/"

# Bird sprites
bird_colors = ['red', 'blue', 'yellow']
bird_sprites = {}
for color in bird_colors:
    bird_sprites[color] = {
        'downflap': pygame.image.load(SPRITE_PATH + f'{color}bird-downflap.png'),
        'midflap': pygame.image.load(SPRITE_PATH + f'{color}bird-midflap.png'),
        'upflap': pygame.image.load(SPRITE_PATH + f'{color}bird-upflap.png')
    }

# Number sprites
number_sprites = {}
for i in range(10):
    try:
        number_sprites[str(i)] = pygame.image.load(SPRITE_PATH + f"{i}.png")
    except:
        number_sprites[str(i)] = None

# UI sprites
try:
    game_over_img = pygame.image.load(SPRITE_PATH + "gameover.png")
    message_img = pygame.image.load(SPRITE_PATH + "message.png")
    box_img = pygame.image.load(SPRITE_PATH + "box.png")
    score_img = pygame.image.load(SPRITE_PATH + "score.png")
    highscore_img = pygame.image.load(SPRITE_PATH + "highscore.png")
    continue_img = pygame.image.load(SPRITE_PATH + "continue.png")
    
    # Scale sprites
    game_over_img = pygame.transform.scale(game_over_img, (200, 50))
    box_img = pygame.transform.scale(box_img, (300, 200))
    score_img = pygame.transform.scale(score_img, (100, 30))
    highscore_img = pygame.transform.scale(highscore_img, (150, 30))
    continue_img = pygame.transform.scale(continue_img, (250, 30))
except:
    game_over_img = message_img = box_img = score_img = highscore_img = continue_img = None

# Background
current_time = time.localtime()
bg_name = "background-night.png" if current_time.tm_hour >= 18 or current_time.tm_hour < 6 else "background-day.png"
background_image = pygame.image.load(SPRITE_PATH + bg_name)
background_image = pygame.transform.scale(background_image, (WIDTH, HEIGHT))

# Pipes
pipe_colors = ['green', 'red']
pipe_sprites = {}
for color in pipe_colors:
    pipe_img = pygame.image.load(SPRITE_PATH + f'{color}pipe.png')
    pipe_sprites[color] = {
        'top': pygame.transform.flip(pipe_img, False, True),
        'bottom': pipe_img
    }

# Base
base = pygame.image.load(SPRITE_PATH + "base.png")
base_height = base.get_height()
base = pygame.transform.scale(base, (WIDTH, base_height))

# Game state variables
bird = pygame.Rect(100, HEIGHT // 2, BIRD_HITBOX_WIDTH, BIRD_HITBOX_HEIGHT)
bird_velocity = 0
bird_color = random.choice(bird_colors)
bird_state = 'downflap'
pipes = []
last_pipe_time = pygame.time.get_ticks()
passed_pipes = set()
pipe_counter = 0
score = 0
high_score = 0
game_active = False
game_over = False
bird_death_animation = False
death_velocity = 0
death_time = 0
first_game_start = True

# Game functions
def load_high_score():
    global high_score
    try:
        if os.path.exists(SCORE_FILE):
            with open(SCORE_FILE, 'r') as f:
                data = json.load(f)
                high_score = data.get('high_score', 0)
    except:
        high_score = 0

def save_high_score():
    try:
        os.makedirs(os.path.dirname(SCORE_FILE), exist_ok=True)
        with open(SCORE_FILE, 'w') as f:
            json.dump({'high_score': high_score}, f)
    except:
        pass

def reset_game():
    global bird, bird_velocity, pipes, score, game_active, game_over
    global last_pipe_time, bird_color, bird_state, passed_pipes
    global pipe_counter, bird_death_animation, death_time, first_game_start
    
    bird = pygame.Rect(100, HEIGHT // 2, BIRD_HITBOX_WIDTH, BIRD_HITBOX_HEIGHT)
    bird_velocity = -2 if first_game_start else 0  # Gentle initial push
    pipes.clear()
    passed_pipes.clear()
    pipe_counter = 0
    score = 0
    game_active = True
    game_over = False
    bird_death_animation = False
    death_time = 0
    last_pipe_time = pygame.time.get_ticks()
    bird_color = random.choice(bird_colors)
    bird_state = 'downflap'
    sfx_button.play()
    first_game_start = False

def get_current_pipe_gap():
    """Returns the pipe gap based on current score"""
    # Base gap decreases up to score 30, then levels off
    score_clamp = min(score, 30)
    gap_reduction = score_clamp * 2  # Reduces gap by up to 60 pixels
    return max(BASE_PIPE_GAP - gap_reduction, 90)  # Never go below 90 pixels

def get_pipe_variation():
    """Returns how much vertical variation to apply based on score"""
    # More variation as score increases, up to a maximum
    return min(score * 2, 100)  # Up to 100 pixels of extra variation

def add_pipe():
    global pipe_counter
    current_gap = get_current_pipe_gap()
    extra_variation = get_pipe_variation()
    
    min_gap_y = 100 + extra_variation//2
    max_gap_y = HEIGHT - current_gap - min_gap_y - base_height - extra_variation//2
    
    if max_gap_y < min_gap_y:
        max_gap_y = min_gap_y + 50
    
    gap_y = random.randint(min_gap_y, max_gap_y)
    pipe_color = random.choice(pipe_colors)
    pipe_id = pipe_counter
    pipe_counter += 1
    
    # Hitboxes centered in visual pipes with exact gap
    pipe_x = WIDTH
    top_hitbox = pygame.Rect(
        pipe_x + (PIPE_WIDTH - PIPE_HITBOX_WIDTH)//2,
        0,
        PIPE_HITBOX_WIDTH,
        gap_y
    )
    bottom_hitbox = pygame.Rect(
        pipe_x + (PIPE_WIDTH - PIPE_HITBOX_WIDTH)//2,
        gap_y + current_gap,
        PIPE_HITBOX_WIDTH,
        HEIGHT - gap_y - current_gap - base_height
    )
    
    pipes.append({
        'top_hitbox': top_hitbox,
        'bottom_hitbox': bottom_hitbox,
        'color': pipe_color,
        'id': pipe_id,
        'gap_y': gap_y
    })

def move_pipes():
    global score
    for pipe in pipes[:]:
        pipe['top_hitbox'].x -= 3
        pipe['bottom_hitbox'].x -= 3
        
        if pipe['id'] not in passed_pipes and pipe['top_hitbox'].x + PIPE_WIDTH < bird.x:
            passed_pipes.add(pipe['id'])
            score += 1
            sfx_point.play()
    
    pipes[:] = [p for p in pipes if p['top_hitbox'].x + PIPE_WIDTH > 0]

def draw_pipes():
    for pipe in pipes:
        color = pipe['color']
        gap_y = pipe['gap_y']
        x_pos = pipe['top_hitbox'].x - (PIPE_WIDTH - PIPE_HITBOX_WIDTH)//2
        
        top_pipe_height = gap_y
        if top_pipe_height > 0:
            scaled_top = pygame.transform.scale(pipe_sprites[color]['top'], (PIPE_WIDTH, top_pipe_height))
            screen.blit(scaled_top, (x_pos, 0))
        
        bottom_pipe_y = gap_y + get_current_pipe_gap()
        bottom_pipe_height = HEIGHT - bottom_pipe_y - base_height
        
        if bottom_pipe_height > 0:
            scaled_bottom = pygame.transform.scale(pipe_sprites[color]['bottom'], (PIPE_WIDTH, bottom_pipe_height))
            screen.blit(scaled_bottom, (x_pos, bottom_pipe_y))

def check_collision():
    global game_active, game_over, bird_death_animation, death_velocity, death_time
    
    # Create slightly tighter bird hitbox (2px padding all around)
    bird_hitbox = pygame.Rect(
        bird.x + 2,
        bird.y + 2,
        BIRD_HITBOX_WIDTH - 4,
        BIRD_HITBOX_HEIGHT - 4
    )
    
    for pipe in pipes:
        # Pipe hitboxes are exactly the gap size, but slightly narrower than visual
        top_pipe_hitbox = pipe['top_hitbox']
        bottom_pipe_hitbox = pipe['bottom_hitbox']
        
        if (bird_hitbox.colliderect(top_pipe_hitbox) or 
            bird_hitbox.colliderect(bottom_pipe_hitbox)):
            sfx_hit.play()
            sfx_die.play()
            game_active = False
            game_over = True
            bird_death_animation = True
            death_velocity = bird_velocity
            death_time = pygame.time.get_ticks()
            return
    
    if bird.top <= 0 or bird.bottom >= HEIGHT - base_height:
        sfx_hit.play()
        sfx_die.play()
        game_active = False
        game_over = True
        bird_death_animation = True
        death_velocity = bird_velocity
        death_time = pygame.time.get_ticks()

def draw_score():
    score_str = str(score)
    digit_width = 24
    start_x = 10
    
    for i, digit in enumerate(score_str):
        if number_sprites.get(digit) is not None:
            screen.blit(number_sprites[digit], (start_x + i * digit_width, 10))
        else:
            digit_surface = score_font.render(digit, True, (255, 255, 255))
            screen.blit(digit_surface, (start_x + i * digit_width, 10))

def draw_high_score():
    score_str = str(high_score)
    digit_width = 24
    start_x = WIDTH - len(score_str) * digit_width - 10
    
    for i, digit in enumerate(score_str):
        if number_sprites.get(digit) is not None:
            screen.blit(number_sprites[digit], (start_x + i * digit_width, 10))
        else:
            digit_surface = score_font.render(digit, True, (255, 255, 255))
            screen.blit(digit_surface, (start_x + i * digit_width, 10))

def draw_game_over():
    if box_img:
        box_rect = box_img.get_rect(center=(WIDTH//2, HEIGHT//2))
        screen.blit(box_img, box_rect)
    
    if game_over_img:
        game_over_rect = game_over_img.get_rect(center=(WIDTH//2, HEIGHT//2 - 70))
        screen.blit(game_over_img, game_over_rect)
    
    box_center_x = WIDTH // 2
    box_center_y = HEIGHT // 2
    
    if score_img:
        score_text_rect = score_img.get_rect(midright=(box_center_x - 10, box_center_y - 20))
        screen.blit(score_img, score_text_rect)
    
    score_str = str(score)
    digit_width = 24
    score_start_x = box_center_x + 30
    score_y = box_center_y - 25
    
    for i, digit in enumerate(score_str):
        if number_sprites.get(digit) is not None:
            screen.blit(number_sprites[digit], (score_start_x + i * digit_width, score_y))
        else:
            digit_surface = score_font.render(digit, True, (255, 255, 255))
            screen.blit(digit_surface, (score_start_x + i * digit_width, score_y))
    
    if highscore_img:
        highscore_text_rect = highscore_img.get_rect(midright=(box_center_x - 10, box_center_y + 20))
        screen.blit(highscore_img, highscore_text_rect)
    
    high_score_str = str(high_score)
    high_score_start_x = box_center_x + 30
    high_score_y = box_center_y + 15
    
    for i, digit in enumerate(high_score_str):
        if number_sprites.get(digit) is not None:
            screen.blit(number_sprites[digit], (high_score_start_x + i * digit_width, high_score_y))
        else:
            digit_surface = score_font.render(digit, True, (255, 255, 0))
            screen.blit(digit_surface, (high_score_start_x + i * digit_width, high_score_y))
    
    current_time = pygame.time.get_ticks()
    if current_time - death_time > DEATH_COOLDOWN:
        if continue_img:
            continue_rect = continue_img.get_rect(center=(box_center_x, box_center_y + 70))
            screen.blit(continue_img, continue_rect)
        else:
            restart_text = score_font.render("Press SPACE or Click to restart", True, (255, 255, 255))
            screen.blit(restart_text, (box_center_x - restart_text.get_width()//2, box_center_y + 80))

def update_bird_state():
    global bird_state
    if bird_velocity < 0:
        bird_state = 'upflap'
    elif bird_velocity > 0:
        bird_state = 'downflap'
    else:
        bird_state = 'midflap'

def handle_death_animation():
    global bird, death_velocity
    death_velocity += GRAVITY
    bird.y += int(death_velocity)
    
    if bird.bottom >= HEIGHT - base_height:
        bird.bottom = HEIGHT - base_height

# Load initial high score
load_high_score()

# Main game loop
running = True
while running:
    screen.blit(background_image, (0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                current_time = pygame.time.get_ticks()
                if game_active:
                    bird_velocity = FLAP_POWER
                    sfx_wing.play()
                elif game_over and current_time - death_time > DEATH_COOLDOWN:
                    reset_game()
                else:
                    reset_game()
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                current_time = pygame.time.get_ticks()
                if game_active:
                    bird_velocity = FLAP_POWER
                    sfx_wing.play()
                elif game_over and current_time - death_time > DEATH_COOLDOWN:
                    reset_game()
                else:
                    reset_game()

    if game_active:
        # Apply reduced gravity for initial descent if needed
        current_gravity = GRAVITY * 0.5 if first_game_start and bird.y < HEIGHT // 2 else GRAVITY
        bird_velocity += current_gravity
        bird.y += int(bird_velocity)

        update_bird_state()

        current_time = pygame.time.get_ticks()
        if current_time - last_pipe_time > PIPE_FREQ:
            add_pipe()
            last_pipe_time = current_time

        move_pipes()
        draw_pipes()
        check_collision()
        screen.blit(bird_sprites[bird_color][bird_state], bird)
        draw_score()
        draw_high_score()

    elif game_over:
        draw_pipes()
        if bird_death_animation:
            handle_death_animation()
        screen.blit(bird_sprites[bird_color]['downflap'], bird)
        draw_game_over()

        if score > high_score:
            high_score = score
            save_high_score()

    else:
        if message_img:
            screen.blit(message_img, (WIDTH//2 - message_img.get_width()//2, HEIGHT//2 - 100))
        else:
            welcome_text = font.render("Press SPACE or Click to Start", True, (255, 255, 255))
            screen.blit(welcome_text, (WIDTH//2 - welcome_text.get_width()//2, HEIGHT//2))

    screen.blit(base, (0, HEIGHT - base_height))
    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()
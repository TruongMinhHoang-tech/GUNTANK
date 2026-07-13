import pygame
import sys
import math
import random

pygame.init()
pygame.mixer.init()


WIDTH, HEIGHT = 1280, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
FPS = 60


WHITE = (255, 255, 255); BLACK = (0, 0, 0); GRAY = (200, 200, 200); DARK_GRAY = (100, 100, 100)
RED = (255, 50, 50); GREEN = (50, 200, 50); BLUE = (50, 150, 255); GOLD = (255, 215, 0)
CRIT_COLOR = (255, 0, 50)

font_huge = pygame.font.SysFont("Arial", 60, bold=True)
font_large = pygame.font.SysFont("Arial", 40, bold=True)
font_medium = pygame.font.SysFont("Arial", 28, bold=True)
font_small = pygame.font.SysFont("Arial", 18, bold=True)

def load_image(filename, size, color):
    try:
        img = pygame.image.load(filename).convert_alpha()
        return pygame.transform.scale(img, size)
    except:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill(color)
        return surf

def load_sound(filename):
    try: return pygame.mixer.Sound(filename)
    except: return None


img_bg_menu = load_image("bg_menu(1).png", (WIDTH, HEIGHT), WHITE)
img_tank = [
    load_image("tank_basic.png", (50, 50), GREEN),
    load_image("tank_speed.png", (50, 50), BLUE),
    load_image("tank_heavy.png", (60, 60), DARK_GRAY),
    load_image("tank_tech.png", (50, 50), (0, 255, 255))
]
img_enemy = load_image("enemy.png", (40, 40), RED)
img_bullet = load_image("bullet.png", (10, 10), BLACK)
img_missile = load_image("missle.png", (100, 100), RED)
img_coin = load_image("coin.png", (15, 15), GOLD)
img_laser = load_image("laser.png", (100, 100), BLUE)
img_ring = load_image("ring.png", (250, 250), RED)

sfx_click = load_sound("sfx_click.wav") 
sfx_shoot = load_sound("sfx_shoot.mp3")
sfx_monster_die = load_sound("sfx_monster_die.mp3") 
sfx_level_up = load_sound("sfx_levelup.mp3")
music_menu = "music_menu.mp3"
music_game = "music_game.mp3"
volume = 0.5

def play_sound(sfx):
    if sfx: sfx.play()


player_data = {
    "gold": 20000, 
    "unlocked_tanks": [0], 
    "upgrades": {"hp": 0, "dmg": 0, "crit_r": 0, "crit_d": 0}
}
tank_prices = {0: 0, 1: 5000, 2: 4500, 3: 8000}
tank_names = ["Basic Tank", "Missile Tank (Missile)", "Armored Tank (Fire Ring)", "Tech Tank (Laser)"]

class Button:
    def __init__(self, x, y, w, h, text, color=GRAY):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text; self.color = color; self.original_y = y 

    def draw(self, surface):
        m_pos = pygame.mouse.get_pos()
        main_color = (min(self.color[0]+30, 255), min(self.color[1]+30, 255), min(self.color[2]+30, 255)) if self.rect.collidepoint(m_pos) else self.color
        
        shadow_rect = self.rect.copy(); shadow_rect.y += 5 
        pygame.draw.rect(surface, DARK_GRAY, shadow_rect, border_radius=10)
        pygame.draw.rect(surface, main_color, self.rect, border_radius=10)
        pygame.draw.rect(surface, BLACK, self.rect, width=2, border_radius=10)

        txt_surf = font_medium.render(self.text, True, BLACK)
        surface.blit(txt_surf, txt_surf.get_rect(center=self.rect.center))

    def is_clicked(self, pos, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(pos):
                self.rect.y += 5
                play_sound(sfx_click)
                return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.rect.y = self.original_y
        return False

class FloatingText:
    def __init__(self, x, y, text, is_crit):
        self.x = x; self.y = y
        self.text = text; self.is_crit = is_crit
        self.life = 40
        
    def update(self):
        self.y -= 2
        self.life -= 1
        
    def draw(self, surface):
        font = font_large if self.is_crit else font_small
        color = CRIT_COLOR if self.is_crit else DARK_GRAY
        txt = font.render(self.text, True, color)
        surface.blit(txt, txt.get_rect(center=(self.x, self.y)))

class Player:
    def __init__(self, tank_type):
        self.x, self.y = WIDTH // 2, HEIGHT // 2
        self.tank_type = tank_type
        self.image = img_tank[tank_type]
        self.rect = self.image.get_rect(center=(self.x, self.y))
        
        self.max_hp = 100 + player_data["upgrades"]["hp"] * 20
        self.hp = self.max_hp
        self.speed = 4.0
        self.dmg = 10 + player_data["upgrades"]["dmg"] * 3
        self.crit_r = 5 + player_data["upgrades"]["crit_r"] * 2 
        self.crit_d = 150 + player_data["upgrades"]["crit_d"] * 10
        self.fire_rate = 500
        
        self.pierce = 1 
        self.magnet = 60 
        self.lifesteal = 0
        self.gold_mult = 1.0
        
        if tank_type == 1: self.max_hp *= 0.8; self.hp = self.max_hp; self.fire_rate = 300; self.crit_r += 10
        elif tank_type == 2: self.max_hp *= 2.0; self.hp = self.max_hp; self.speed = 2.5; self.dmg *= 1.5
        elif tank_type == 3: self.pierce = 3; self.dmg *= 1.2; self.lifesteal = 2; self.crit_r += 30; self.fire_rate = 300; self.speed = 5.0
            
        self.last_shot = 0; self.last_skill = 0
        self.level = 1; self.exp = 0; self.exp_needed = 50; self.in_game_gold = 0

    def move(self):
        keys = pygame.key.get_pressed()
        if (keys[pygame.K_w] or keys[pygame.K_UP]) and self.y > 0: self.y -= self.speed
        if (keys[pygame.K_s] or keys[pygame.K_DOWN]) and self.y < HEIGHT: self.y += self.speed
        if (keys[pygame.K_a] or keys[pygame.K_LEFT]) and self.x > 0: self.x -= self.speed
        if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) and self.x < WIDTH: self.x += self.speed
        self.rect.center = (self.x, self.y)

    def auto_shoot(self, enemies, bullets):
        if not enemies: return
        now = pygame.time.get_ticks()
        if now - self.last_shot >= self.fire_rate:
            target = min(enemies, key=lambda e: math.hypot(e.x - self.x, e.y - self.y))
            is_crit = random.randint(1, 100) <= self.crit_r
            final_dmg = int(self.dmg * (self.crit_d / 100)) if is_crit else int(self.dmg)
            
            bullets.append(Bullet(self.x, self.y, target.x, target.y, final_dmg, is_crit, pierce=self.pierce))
            play_sound(sfx_shoot)
            self.last_shot = now

    def auto_skill(self, enemies, bullets):
        if not enemies: return
        now = pygame.time.get_ticks()
        
        # TANK 1
        if self.tank_type == 1 and now - self.last_skill >= 3000: 
            target = random.choice(enemies)
            is_crit = random.randint(1, 100) <= self.crit_r
            final_dmg = int(self.dmg * 3 * (self.crit_d / 100)) if is_crit else int(self.dmg * 3)
            bullets.append(Bullet(self.x, self.y, target.x, target.y, final_dmg, is_crit, is_missile=True))
            self.last_skill = now
            
        # TANK 2
        elif self.tank_type == 2 and now - self.last_skill >= 2500:
            is_crit = random.randint(1, 100) <= self.crit_r
            final_dmg = int(self.dmg * 2 * (self.crit_d / 100)) if is_crit else int(self.dmg * 2)
            bullets.append(Bullet(self.x, self.y, self.x, self.y, final_dmg, is_crit, is_ring=True, pierce=999))
            self.last_skill = now
            
        # TANK 3
        elif self.tank_type == 3 and now - self.last_skill >= 4000:
            target = random.choice(enemies)
            is_crit = random.randint(1, 100) <= self.crit_r
            final_dmg = int(self.dmg * 4 * (self.crit_d / 100)) if is_crit else int(self.dmg * 4)
            bullets.append(Bullet(self.x, self.y, target.x, target.y, final_dmg, is_crit, is_laser=True, pierce=999))
            self.last_skill = now

    def draw(self, surface):
        surface.blit(self.image, self.rect)
        pygame.draw.rect(surface, RED, (self.rect.x, self.rect.y - 15, 50, 5))
        pygame.draw.rect(surface, GREEN, (self.rect.x, self.rect.y - 15, 50 * max(0, self.hp/self.max_hp), 5))

class Enemy:
    def __init__(self, time_elapsed):
        self.x = random.choice([-50, WIDTH + 50]) if random.choice([True, False]) else random.randint(-50, WIDTH + 50)
        self.y = random.randint(-50, HEIGHT + 50) if self.x in [-50, WIDTH + 50] else random.choice([-50, HEIGHT + 50])
        self.rect = img_enemy.get_rect(center=(self.x, self.y))
        
        scale = 1 + (time_elapsed / 30000)
        self.hp = 20 * scale; self.dmg = 5 * scale; self.speed = random.uniform(1.0, 2.0)

    def update(self, px, py):
        angle = math.atan2(py - self.y, px - self.x)
        self.x += math.cos(angle) * self.speed
        self.y += math.sin(angle) * self.speed
        self.rect.center = (self.x, self.y)

    def draw(self, surface):
        surface.blit(img_enemy, self.rect)


class Bullet:
    def __init__(self, x, y, tx, ty, dmg, is_crit, is_missile=False, is_laser=False, is_ring=False, pierce=1):
        self.x, self.y = x, y; self.dmg = dmg; self.is_crit = is_crit
        self.is_missile = is_missile
        self.is_laser = is_laser
        self.is_ring = is_ring
        self.pierce = pierce
        self.hit_enemies = [] 
        
        if self.is_ring:
            
            self.speed = 0
            self.vx, self.vy = 0, 0
            self.image = img_ring 
            self.rect = self.image.get_rect(center=(x, y))
            self.life = 15 
        else:
           
            self.speed = 30 if self.is_laser else (6 if self.is_missile else 12)
            angle = math.atan2(ty - y, tx - x)
            self.vx = math.cos(angle) * self.speed; self.vy = math.sin(angle) * self.speed
            
            if self.is_laser:
              
                self.image = img_laser
                
                self.image = pygame.transform.rotate(self.image, math.degrees(-angle))
                self.rect = self.image.get_rect(center=(x, y))
                self.life = 60 
            else:
                self.image = img_missile if self.is_missile else img_bullet
                self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        self.x += self.vx; self.y += self.vy
        self.rect.center = (self.x, self.y)
        if self.is_ring or self.is_laser:
            self.life -= 1

    def draw(self, surface): 
        if self.is_ring:
            pygame.draw.circle(surface, (255, 100, 0), (int(self.x), int(self.y)), 125, width=6)
            pygame.draw.circle(surface, (255, 200, 0), (int(self.x), int(self.y)), 115, width=2)
        else:
            surface.blit(self.image, self.rect)

class Drop:
    def __init__(self, x, y):
        self.rect = img_coin.get_rect(center=(x, y))
        self.value = random.randint(10, 20)

    def draw(self, surface): surface.blit(img_coin, self.rect)

def state_menu():
    btn_start = Button(WIDTH//2 - 100, 300, 200, 60, "READY")
    btn_setting = Button(WIDTH//2 - 100, 380, 200, 60, "SETTING")
    btn_exit = Button(WIDTH//2 - 100, 460, 200, 60, "EXIT")
    
    try:
        pygame.mixer.music.load(music_menu)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(-1)
    except: pass

    while True:
        screen.blit(img_bg_menu, (0,0))
        m_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: sys.exit()
            if btn_start.is_clicked(m_pos, event): return "PREP"
            if btn_setting.is_clicked(m_pos, event): return "SETTING"
            if btn_exit.is_clicked(m_pos, event): sys.exit()

        btn_start.draw(screen); btn_setting.draw(screen); btn_exit.draw(screen)
        pygame.display.flip(); clock.tick(FPS)

def state_setting():
    global volume
    btn_up = Button(WIDTH//2 + 50, 300, 60, 60, "+")
    btn_down = Button(WIDTH//2 - 110, 300, 60, 60, "-")
    btn_back = Button(WIDTH//2 - 100, 450, 200, 60, "RETURN")

    while True:
        screen.fill(WHITE)
        m_pos = pygame.mouse.get_pos()
        
        vol_text = font_large.render(f"SOUND: {int(volume*100)}%", True, BLACK)
        screen.blit(vol_text, (WIDTH//2 - vol_text.get_width()//2, 200))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: sys.exit()
            if btn_up.is_clicked(m_pos, event): 
                volume = min(1.0, volume + 0.1)
                pygame.mixer.music.set_volume(volume)
            if btn_down.is_clicked(m_pos, event): 
                volume = max(0.0, volume - 0.1)
                pygame.mixer.music.set_volume(volume)
            if btn_back.is_clicked(m_pos, event): return "MENU"

        btn_up.draw(screen); btn_down.draw(screen); btn_back.draw(screen)
        pygame.display.flip(); clock.tick(FPS)

def state_preparation():
    btn_back = Button(20, 20, 100, 40, "RETURN")
    btn_exit_corner = Button(WIDTH - 60, 20, 40, 40, "X", RED)
    
    btn_prev = Button(WIDTH//2 - 200, 150, 50, 50, "<")
    btn_next = Button(WIDTH//2 + 150, 150, 50, 50, ">")
    btn_action = Button(WIDTH//2 - 100, 220, 200, 50, "", GREEN) 
    
    up_hp = Button(200, 350, 150, 40, "HP (50G)"); up_dmg = Button(200, 420, 150, 40, "DMG (50G)")
    up_cr = Button(200, 490, 150, 40, "CR (80G)"); up_cd = Button(200, 560, 150, 40, "CRD (80G)")
    
    selected_tank = 0

    while True:
        screen.fill(WHITE)
        m_pos = pygame.mouse.get_pos()
        screen.blit(font_large.render(f"GOLD: {int(player_data['gold'])}", True, GOLD), (WIDTH - 300, 80))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: sys.exit()
            if btn_back.is_clicked(m_pos, event): return "MENU"
            if btn_exit_corner.is_clicked(m_pos, event): sys.exit()
            
            if btn_prev.is_clicked(m_pos, event): selected_tank = (selected_tank - 1) % 4
            if btn_next.is_clicked(m_pos, event): selected_tank = (selected_tank + 1) % 4
            
            if btn_action.is_clicked(m_pos, event):
                if selected_tank in player_data["unlocked_tanks"]: return f"PLAY_{selected_tank}"
                elif player_data["gold"] >= tank_prices[selected_tank]:
                    player_data["gold"] -= tank_prices[selected_tank]
                    player_data["unlocked_tanks"].append(selected_tank)
            
            if up_hp.is_clicked(m_pos, event) and player_data["gold"] >= 50:
                player_data["gold"] -= 50; player_data['upgrades']['hp'] += 1
            if up_dmg.is_clicked(m_pos, event) and player_data["gold"] >= 50:
                player_data["gold"] -= 50; player_data['upgrades']['dmg'] += 1
            if up_cr.is_clicked(m_pos, event) and player_data["gold"] >= 80:
                player_data["gold"] -= 80; player_data['upgrades']['crit_r'] += 1
            if up_cd.is_clicked(m_pos, event) and player_data["gold"] >= 80:
                player_data["gold"] -= 80; player_data['upgrades']['crit_d'] += 1

        screen.blit(img_tank[selected_tank], (WIDTH//2 - 25, 120))
        screen.blit(font_medium.render(tank_names[selected_tank], True, BLACK), (WIDTH//2 - 200, 80))
        if selected_tank in player_data["unlocked_tanks"]: btn_action.text = "START"; btn_action.color = GREEN
        else: btn_action.text = f"BUY ({tank_prices[selected_tank]})"; btn_action.color = GOLD
        
        btn_action.draw(screen); btn_prev.draw(screen); btn_next.draw(screen)

        screen.blit(font_large.render("STAT UPGRADES", True, BLACK), (150, 280))
        screen.blit(font_medium.render(f"+ {player_data['upgrades']['hp']*20} HP", True, GREEN), (380, 350))
        screen.blit(font_medium.render(f"+ {player_data['upgrades']['dmg']*3} DAMAGE", True, RED), (380, 420))
        screen.blit(font_medium.render(f"+ {player_data['upgrades']['crit_r']*2}% CRIT ", True, GOLD), (380, 490))
        screen.blit(font_medium.render(f"+ {player_data['upgrades']['crit_d']*10}% CRIT DAMAGE", True, BLUE), (380, 560))
        
        btn_back.draw(screen); btn_exit_corner.draw(screen)
        up_hp.draw(screen); up_dmg.draw(screen); up_cr.draw(screen); up_cd.draw(screen)
        pygame.display.flip(); clock.tick(FPS)

SKILL_NAMES = [
    "Increase Max HP", "Increase Damage", "Increase Speed", "Increase Fire Rate",
    "Increase Crit Rate", "Increase Crit Damage", "Heal on Kill", 
    "Increase Pickup Range", "Piercing Bullets", "INCREASE GOLD/EXP"
]

def state_playing(tank_type):
    player = Player(tank_type)
    enemies = []; bullets = []; drops = []; floating_texts = []
    start_time = pygame.time.get_ticks(); enemy_spawn_timer = 0
    btn_exit_corner = Button(WIDTH - 60, 20, 40, 40, "X", RED)
    
    is_leveling_up = False
    skill_choices = []
    btn_skills = [Button(WIDTH//2 - 150, 200, 300, 80, ""), Button(WIDTH//2 - 150, 320, 300, 80, ""), Button(WIDTH//2 - 150, 440, 300, 80, "")]
    
    try:
        pygame.mixer.music.load(music_game)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(-1)
    except: pass

    while True:
        screen.fill(WHITE)
        m_pos = pygame.mouse.get_pos()
        now = pygame.time.get_ticks()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: sys.exit()
            
            if is_leveling_up:
                for i in range(3):
                    if btn_skills[i].is_clicked(m_pos, event):
                        chosen_skill = skill_choices[i]
                        if chosen_skill == 0: player.max_hp += 30; player.hp += 30
                        elif chosen_skill == 1: player.dmg += 5
                        elif chosen_skill == 2: player.speed += 0.5
                        elif chosen_skill == 3: player.fire_rate = max(100, player.fire_rate - 50)
                        elif chosen_skill == 4: player.crit_r += 5
                        elif chosen_skill == 5: player.crit_d += 30
                        elif chosen_skill == 6: player.lifesteal += 2
                        elif chosen_skill == 7: player.magnet += 50
                        elif chosen_skill == 8: player.pierce += 1
                        elif chosen_skill == 9: player.gold_mult += 0.5
                        is_leveling_up = False 
            else:
                if btn_exit_corner.is_clicked(m_pos, event): 
                    player_data["gold"] += player.in_game_gold; return "PREP"

        if not is_leveling_up:
            game_time = now - start_time
            spawn_rate = max(200, 800 - (game_time // 200))
            if now - enemy_spawn_timer > spawn_rate:
                enemies.append(Enemy(game_time)); enemy_spawn_timer = now

            player.move(); player.auto_shoot(enemies, bullets); player.auto_skill(enemies, bullets)
            
            for b in bullets[:]:
                b.update()
                
                is_special_skill = getattr(b, 'is_ring', False) or getattr(b, 'is_laser', False)
                if not is_special_skill and (b.x < 0 or b.x > WIDTH or b.y < 0 or b.y > HEIGHT): 
                    bullets.remove(b); continue
                
                if is_special_skill and getattr(b, 'life', 0) <= 0:
                    if b in bullets: bullets.remove(b)
                    continue
                
                for e in enemies[:]:
                    if b.rect.colliderect(e.rect) and e not in b.hit_enemies:
                        if getattr(b, 'is_ring', False) and math.hypot(e.x - b.x, e.y - b.y) > 125:
                            continue
                            
                        e.hp -= b.dmg
                        b.hit_enemies.append(e) 
                        b.pierce -= 1
                        
                        floating_texts.append(FloatingText(e.x, e.y - 20, str(b.dmg), b.is_crit))
                        
                        if b.pierce <= 0 and b in bullets: bullets.remove(b)
                        if e.hp <= 0:
                            play_sound(sfx_monster_die)
                            drops.append(Drop(e.x, e.y))
                            player.hp = min(player.max_hp, player.hp + player.lifesteal) 
                            if e in enemies: enemies.remove(e)
                        break

            for e in enemies[:]:
                e.update(player.x, player.y)
                if e.rect.colliderect(player.rect):
                    player.hp -= e.dmg * 0.1
                    if player.hp <= 0: player_data["gold"] += player.in_game_gold; return "PREP"

            for d in drops[:]:
                if math.hypot(d.rect.centerx - player.x, d.rect.centery - player.y) < player.magnet:
                    val = int(d.value * player.gold_mult)
                    player.exp += val; player.in_game_gold += val
                    drops.remove(d)
                    
                    if player.exp >= player.exp_needed:
                        play_sound(sfx_level_up)
                        player.level += 1
                        player.exp -= player.exp_needed
                        player.exp_needed = int(player.exp_needed * 1.5)
                        is_leveling_up = True
                        skill_choices = random.sample(range(10), 3)
                        for i in range(3): btn_skills[i].text = SKILL_NAMES[skill_choices[i]]

        for d in drops: d.draw(screen)
        for e in enemies: e.draw(screen)
        
        for b in bullets: 
            if getattr(b, 'is_ring', False): b.draw(screen)
        player.draw(screen)
        for b in bullets: 
            if not getattr(b, 'is_ring', False): b.draw(screen)
            
        for ft in floating_texts[:]:
            ft.update(); ft.draw(screen)
            if ft.life <= 0: floating_texts.remove(ft)

        screen.blit(font_medium.render(f"LVL: {player.level} | EXP: {player.exp}/{player.exp_needed}", True, BLUE), (10, 10))
        screen.blit(font_medium.render(f"GOLD: {player.in_game_gold}", True, GOLD), (10, 40))
        btn_exit_corner.draw(screen)

        if is_leveling_up:
            overlay = pygame.Surface((WIDTH, HEIGHT)); overlay.set_alpha(150); overlay.fill(BLACK)
            screen.blit(overlay, (0, 0))
            screen.blit(font_huge.render("LEVEL UP! CHOOSE A SKILL", True, GOLD), (WIDTH//2 - 400, 80))
            for i in range(3): btn_skills[i].draw(screen)

        pygame.display.flip(); clock.tick(FPS)

def main():
    state = "MENU"
    while True:
        if state == "MENU": state = state_menu()
        elif state == "SETTING": state = state_setting()
        elif state == "PREP": state = state_preparation()
        elif state.startswith("PLAY_"): state = state_playing(int(state.split("_")[1]))

if __name__ == "__main__": main()
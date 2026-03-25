import pygame
import random
import os
import math
import ctypes
import json

try:
    myappid = 'pokemining.v1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except:
    pass 

# --- CONFIGURAÇÕES GERAIS ---
GAME_TITLE = "PokeMining"
DEBUG_MODE = False          
SHOW_ITEM_COUNT = True      
DYNAMIC_FONT_SIZE = True    
FIXED_HP_VALUE = 150      

MIN_ITEMS_PER_MAP = 2       
MAX_ITEMS_PER_MAP = 5       
SPAWN_OBSTACLES = True      
MIN_ROCKS = 3               
MAX_ROCKS = 6               

BASE_HAMMER = 6           
BASE_PICK = 3          
WALL_COLLAPSE_PENALTY = 25  

COLOR_TEXT = (255, 250, 230)
COLOR_GOLD = (255, 215, 0)
COLOR_OUTLINE = (20, 20, 20)
# =========================================================

SPECIAL_SIZES = {
    "plume_fossil": (3, 3), "odd_keystone": (4, 4), "thick_bone": (3, 8),
    "star_piece": (3, 3), "horn_fossil": (2, 4), "marine_fossil": (4, 4),
    "fragmento_lapidado": (3, 3), "fragmento_queimado": (3, 3), "heart_scale": (2, 2),
    "jaw_fossil": (3, 4), "everstone": (4, 2), "sail_fossil": (4, 4),
    "old_amber": (4, 4), "lizard_fossil": (4, 4), "cover_fossil": (4, 4),
    "oricalco": (4,4),
}

SPECIAL_MASK_EXCEPTIONS = {
    "plume_fossil": [(0, 2), (2, 0), (2, 1)],
    "thick_bone": [(1, 0), (2, 0), (1, 2), (2, 2),(3, 0), (4, 0), (5, 0), (6, 0), (3, 2), (4, 2),(5, 2), (6, 2)],
    "star_piece": [(0, 0), (0, 2), (2, 0), (2, 2)], "horn_fossil": [(0, 0)],
    "marine_fossil": [(0, 0), (3, 3)], "heart_scale": [(0, 1)], "jaw_fossil": [(0, 0), (1, 3)],
    "sail_fossil": [(0, 2), (0, 3)], "old_amber": [(0, 3), (3, 0)], "lizard_fossil": [(3, 0), (3, 3)],
    "cover_fossil": [(0, 0), (3, 3)], "oricalco": [(0, 0), (0, 3)]
}

INDIVIDUAL_WEIGHTS = { "horn_fossil": 3, "old_amber": 5, "eviolite": 3, "voidstone": 3, "comet_shard": 1, "oricalco": 1, "odd_keystone": 8 }

class MiningGame:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        
        self.screen = pygame.display.set_mode((512, 384))
        pygame.display.set_caption(GAME_TITLE)
        
        try:
            icon = pygame.image.load("assets/ui/layout/icon.ico")
            pygame.display.set_icon(icon)
        except: pass

        self.clock = pygame.time.Clock()
        
        self.state = "MENU"        
        self.prev_state = "MENU"   
        self.settings_tab = "AUDIO"
        self.history_detail_index = None 
        
        saved_data = self.load_save_data()
        
        self.volume = saved_data.get("volume", 0.5)
        self.tool = saved_data.get("tool", "pick")
        
        saved_talents = saved_data.get("talents", {})
        self.talents = {
            "exploracao": saved_talents.get("exploracao", False), 
            "evo": saved_talents.get("evo", False), 
            "passado": saved_talents.get("passado", False), 
            "arqueologo": saved_talents.get("arqueologo", False),
            "martelo1": saved_talents.get("martelo1", False), 
            "martelo2": saved_talents.get("martelo2", False), 
            "conhecimento": saved_talents.get("conhecimento", False)
        }
        
        raw_hist = saved_data.get("history", [])
        self.history = [item for item in raw_hist if isinstance(item, list)]
        self.match_recorded = False 

        self.load_assets()
        self.reset_game()

    def load_save_data(self):
        try:
            if os.path.exists("save_data.json"):
                with open("save_data.json", "r") as f:
                    return json.load(f)
        except: pass
        return {}

    def save_game_data(self):
        data = {
            "volume": self.volume,
            "tool": self.tool,
            "talents": self.talents,
            "history": self.history
        }
        try:
            with open("save_data.json", "w") as f:
                json.dump(data, f)
        except: pass

    def save_match_history(self):
        itens_pegos = []
        for i in self.active_items:
            if i['revealed']:
                itens_pegos.append({'name': i['name'], 'raw_name': i['raw_name']})
                
        self.history.insert(0, itens_pegos)
        self.history = self.history[:15]
        self.save_game_data()

    def draw_text_outlined(self, text, font, color, outline_color, pos, center=False):
        text_surf = font.render(text, True, color)
        outline_surf = font.render(text, True, outline_color)
        x, y = pos
        if center:
            x -= text_surf.get_width() // 2
            y -= text_surf.get_height() // 2
        for ox, oy in [(-1,-1), (1,-1), (-1,1), (1,1)]:
            self.screen.blit(outline_surf, (x + ox, y + oy))
        self.screen.blit(text_surf, (x, y))

    def load_assets(self):
        self.bg = pygame.Surface((512, 384)); self.bg.fill((30, 30, 30))
        self.end_bg = pygame.Surface((512, 384)); self.end_bg.fill((20, 20, 20))
        self.ui_tools = {}
        self.pick_hit = self.hammer_hit = pygame.Surface((0,0))
        self.tile_images = [pygame.Surface((32, 32)) for _ in range(6)]

        try:
            self.snd = {
                "hammer": pygame.mixer.Sound("assets/sounds/hammer-stone.wav"),
                "pick": pygame.mixer.Sound("assets/sounds/pick-stone.wav"),
                "hard": pygame.mixer.Sound("assets/sounds/hard-hit.wav"),
                "collapse": pygame.mixer.Sound("assets/sounds/gameover.wav")
            }
            self.volume_adjust()
        except: self.snd = {}

        try:
            self.bg = pygame.transform.scale(pygame.image.load("assets/ui/layout/miningbg.png").convert_alpha(), (512, 384))
            self.end_bg = pygame.transform.scale(pygame.image.load("assets/ui/background/ending_screen.png").convert_alpha(), (512, 384))
            self.ui_tools = {
                "hammer_on": pygame.image.load("assets/ui/layout/hammer-on.png").convert_alpha(),
                "hammer_off": pygame.image.load("assets/ui/layout/hammer-off.png").convert_alpha(),
                "pick_on": pygame.image.load("assets/ui/layout/pick-on.png").convert_alpha(),
                "pick_off": pygame.image.load("assets/ui/layout/pick-off.png").convert_alpha()
            }
            self.pick_hit = pygame.transform.scale(pygame.image.load("assets/ui/effects/pick_hit.png").convert_alpha(), (96, 96))
            self.hammer_hit = pygame.transform.scale(pygame.image.load("assets/ui/effects/hammer_hit.png").convert_alpha(), (96, 96))
            sheet = pygame.image.load("assets/ui/background/tiles.png").convert_alpha()
            self.tile_images = [pygame.transform.scale(sheet.subsurface(pygame.Rect(0, i*16, 16, 16)), (32, 32)) for i in range(6)]
        except: pass

        self.obstacle_templates = []
        m_path = "assets/matriz"
        if os.path.exists(m_path):
            for f in os.listdir(m_path):
                if f.endswith(".png"):
                    img = pygame.image.load(os.path.join(m_path, f)).convert_alpha()
                    w_b, h_b = max(1, int(round(img.get_width()/16.0))), max(1, int(round(img.get_height()/16.0)))
                    self.obstacle_templates.append({
                        'img': pygame.transform.scale(img, (w_b*32, h_b*32)),
                        'mask': [[img.get_at((int((c+0.5)*(img.get_width()/w_b)), int((r+0.5)*(img.get_height()/h_b))))[3] > 128 for c in range(w_b)] for r in range(h_b)],
                        'w': w_b, 'h': h_b
                    })

        self.item_sprites = {}
        self.f_weights = {"small_spheres": 50, "gems": 35, "items": 25, "thick_bone": 25, "nugget": 15, "evo": 20, "fosseis": 8, "plates": 3, "rare_treasure": 2, "big_spheres": 5}
        folders = {"evo": (2,2), "fosseis": (4,4), "gems": (1,1), "items": (2,2), "plates": (4,3), "small_spheres": (2,2), "rare_treasure": (3,3), "nugget": (2,2), "thick_bone": (2,4), "big_spheres": (3,3)}
        for fld, sz in folders.items():
            path = f"assets/{fld}"
            if os.path.exists(path):
                for f in os.listdir(path):
                    if f.endswith(".png"):
                        name = f.replace(".png", "")
                        real_sz = SPECIAL_SIZES.get(name, sz)
                        self.item_sprites[name] = {'img': pygame.image.load(os.path.join(path, f)).convert_alpha(), 'w': real_sz[0], 'h': real_sz[1], 'folder': fld}

    def volume_adjust(self):
        for sound in self.snd.values(): sound.set_volume(self.volume)

    def reset_game(self):
        self.max_hp = FIXED_HP_VALUE + (50 if self.talents["exploracao"] else 0)
        self.wall_hp = self.max_hp
        self.game_over, self.won = False, False
        self.grid = [[random.randint(3, 6) for _ in range(13)] for _ in range(10)]
        self.item_mask = [[False for _ in range(13)] for _ in range(10)]
        self.rock_mask = [[False for _ in range(13)] for _ in range(10)]
        self.active_items, self.placed_rocks = [], []
        self.show_hit, self.hit_pos, self.hit_type = 0, (0,0), "pick"
        self.fade_alpha, self.played_collapse = 0, False
        self.match_recorded = False 
        
        self.spawn_items()
        if SPAWN_OBSTACLES: self.spawn_rocks()

    def spawn_items(self):
        pool = []
        for name, d in self.item_sprites.items():
            base_w = self.f_weights.get(d['folder'], 10)
            if d['folder'] == "evo" and self.talents["evo"]: base_w *= 2.0
            if d['folder'] == "fosseis" and self.talents["passado"]: base_w *= 2.0
            if d['folder'] in ["rare_treasure", "nugget"] and self.talents["conhecimento"]: base_w *= 2.0
            pool.extend([name] * int(base_w * INDIVIDUAL_WEIGHTS.get(name, 10)))
        
        min_it = 3 if self.talents["arqueologo"] else MIN_ITEMS_PER_MAP
        max_it = 6 if self.talents["arqueologo"] else MAX_ITEMS_PER_MAP
        
        for _ in range(random.randint(min_it, max_it)):
            if not pool: break
            name = random.choice(pool)
            d = self.item_sprites[name]
            for _ in range(100):
                ix, iy = random.randint(0, 13 - d['w']), random.randint(0, 10 - d['h'])
                if not any(self.item_mask[iy+r][ix+c] for r in range(d['h']) for c in range(d['w'])):
                    exc = SPECIAL_MASK_EXCEPTIONS.get(name, [])
                    for r in range(d['h']):
                        for c in range(d['w']):
                            if (r, c) not in exc: self.item_mask[iy+r][ix+c] = True
                    self.active_items.append({'img': pygame.transform.scale(d['img'], (d['w']*32, d['h']*32)), 'raw_name': name, 'name': name.replace('_', ' ').title(), 'x': ix, 'y': iy, 'w': d['w'], 'h': d['h'], 'revealed': False, 'reveal_time': 0})
                    
                    qtd = pool.count(name)
                    pool = [i for i in pool if i != name]
                    pool.extend([name] * max(1, int(qtd * 0.15)))
                    break

    def spawn_rocks(self):
        if not self.obstacle_templates: return
        for _ in range(random.randint(MIN_ROCKS, MAX_ROCKS)):
            tmpl = random.choice(self.obstacle_templates)
            for _ in range(100):
                rx, ry = random.randint(0, 13 - tmpl['w']), random.randint(0, 10 - tmpl['h'])
                if not any(tmpl['mask'][r][c] and (self.item_mask[ry+r][rx+c] or self.rock_mask[ry+r][rx+c]) for r in range(tmpl['h']) for c in range(tmpl['w'])):
                    for r in range(tmpl['h']):
                        for c in range(tmpl['w']):
                            if tmpl['mask'][r][c]: self.rock_mask[ry+r][rx+c] = True
                    self.placed_rocks.append({'img': tmpl['img'], 'x': rx, 'y': ry}); break

    def handle_click(self, pos):
        mx, my = pos
        
        # --- MENUS ---
        if self.state == "MENU":
            if 206 <= mx <= 306:
                if 140 <= my <= 165: self.state = "GAME"; self.reset_game()
                elif 185 <= my <= 210: self.state = "TALENTS"
                elif 230 <= my <= 255: self.state = "SETTINGS"; self.prev_state = "MENU"
                elif 275 <= my <= 300: self.state = "HISTORY"
                elif 320 <= my <= 345: 
                    self.save_game_data() 
                    pygame.quit(); exit()
            return
            
        if self.state == "HISTORY":
            if self.history_detail_index is not None:
                self.history_detail_index = None
                return
                
            for i, match in enumerate(self.history):
                col = i % 3
                row = i // 3
                x = 100 + col * 156
                y = 120 + row * 45
                if x - 60 <= mx <= x + 60 and y - 15 <= my <= y + 15:
                    self.history_detail_index = i
                    return
            return
            
        if self.state == "TALENTS":
            t_keys = ["exploracao", "arqueologo", "martelo1", "martelo2", "evo", "passado", "conhecimento"]
            for i, key in enumerate(t_keys):
                cy = 100 + i * 32
                if 40 <= mx <= 460 and cy <= my <= cy + 20:
                    self.talents[key] = not self.talents[key]
            return
            
        if self.state == "SETTINGS":
            if 150 <= mx <= 350 and 150 <= my <= 190: 
                self.volume = (mx-150)/200; self.volume_adjust()
            
            if self.prev_state == "GAME":
                if 130 <= mx <= 382 and 240 <= my <= 270:
                    self.save_game_data() 
                    self.state = "MENU" 
            return

        # --- IN-GAME ---
        if self.game_over: return
        
        if 437 <= mx <= 497:
            if 115 <= my <= 205: self.tool = "hammer"; self.save_game_data(); return
            if 258 <= my <= 348: self.tool = "pick"; self.save_game_data(); return
        
        col, row = mx // 32, (my - 64) // 32
        if 0 <= row < 10 and 0 <= col < 13:
            self.show_hit, self.hit_pos, self.hit_type = 6, (col*32, row*32+64), self.tool
            if self.grid[row][col] == 0 and self.rock_mask[row][col]:
                if "hard" in self.snd: self.snd["hard"].play()
                self.wall_hp -= WALL_COLLAPSE_PENALTY
            else:
                if self.tool == "pick":
                    if "pick" in self.snd: self.snd["pick"].play()
                    self.wall_hp -= BASE_PICK
                    self.grid[row][col] = max(0, self.grid[row][col]-2)
                    for r, c in [(row-1, col), (row+1, col), (row, col-1), (row, col+1)]:
                        if 0<=r<10 and 0<=c<13: self.grid[r][c] = max(0, self.grid[r][c]-1)
                else:
                    if "hammer" in self.snd: self.snd["hammer"].play()
                    final_hammer_dmg = BASE_HAMMER - (1 if self.talents["martelo1"] else 0) + (4 if self.talents["martelo2"] else 0)
                    self.wall_hp -= final_hammer_dmg
                    for r in range(row-1, row+2):
                        for c in range(col-1, col+2):
                            if 0<=r<10 and 0<=c<13: self.grid[r][c] = max(0, self.grid[r][c]-(3 if r==row and c==col else 2))
                    if self.talents["martelo2"]:
                        for r, c in [(row-2, col), (row+2, col), (row, col-2), (row, col+2)]:
                            if 0<=r<10 and 0<=c<13: self.grid[r][c] = max(0, self.grid[r][c]-2)

            for item in self.active_items:
                if not item['revealed']:
                    exc = SPECIAL_MASK_EXCEPTIONS.get(item['raw_name'], [])
                    if all(self.grid[item['y']+r][item['x']+c] == 0 for r in range(item['h']) for c in range(item['w']) if (r, c) not in exc):
                        item['revealed'] = True; item['reveal_time'] = pygame.time.get_ticks()
        
        if all(self.grid[r][c] == 0 for r in range(10) for c in range(13) if self.item_mask[r][c]):
            self.won, self.game_over = True, True
        elif self.wall_hp <= 0: 
            self.wall_hp, self.game_over = 0, True
            
        if self.game_over and not self.match_recorded:
            self.save_match_history()
            self.match_recorded = True

    # --- DRAW
    def draw_menu(self):
        self.screen.blit(self.end_bg, (0, 0))
        self.draw_text_outlined(GAME_TITLE, pygame.font.SysFont("Verdana", 24, bold=True), COLOR_GOLD, COLOR_OUTLINE, (256, 70), center=True)
        
        mx, my = pygame.mouse.get_pos()
        options = ["Jogar", "Selecionar Talentos", "Som", "Itens Passados", "Sair"]
        for i, text in enumerate(options):
            y_pos = 150 + i * 45
            is_hover = 160 <= mx <= 352 and y_pos - 15 <= my <= y_pos + 15
            color = COLOR_GOLD if is_hover else COLOR_TEXT
            self.draw_text_outlined(text, pygame.font.SysFont("Verdana", 16, bold=True), color, COLOR_OUTLINE, (256, y_pos), center=True)

    def draw_history(self):
        self.screen.blit(self.end_bg, (0, 0))
        
        if self.history_detail_index is None:
            self.draw_text_outlined("HISTÓRICO (ÚLTIMAS 15 PARTIDAS)", pygame.font.SysFont("Verdana", 20, bold=True), COLOR_GOLD, COLOR_OUTLINE, (256, 40), center=True)
            
            f_hist = pygame.font.SysFont("Courier New", 14, bold=True)
            if not self.history:
                self.draw_text_outlined("Nenhuma partida registrada ainda.", f_hist, COLOR_TEXT, COLOR_OUTLINE, (256, 150), center=True)
            else:
                mx, my = pygame.mouse.get_pos()
                for i, match in enumerate(self.history):
                    col = i % 3
                    row = i // 3
                    x = 100 + col * 156
                    y = 120 + row * 45
                    
                    qtd = len(match) if isinstance(match, list) else 0
                    is_hover = (x - 60 <= mx <= x + 60) and (y - 15 <= my <= y + 15)
                    color = COLOR_GOLD if is_hover else COLOR_TEXT
                    
                    self.draw_text_outlined(f"#{i+1}: {qtd} itens", f_hist, color, COLOR_OUTLINE, (x, y), center=True)
                    
            self.draw_text_outlined("Pressione ESC para voltar ao Menu", pygame.font.SysFont("Verdana", 12, bold=True), (150,150,150), COLOR_OUTLINE, (256, 350), center=True)
        
        else:
            match = self.history[self.history_detail_index]
            self.draw_text_outlined(f"DETALHES DA PARTIDA #{self.history_detail_index + 1}", pygame.font.SysFont("Verdana", 20, bold=True), COLOR_GOLD, COLOR_OUTLINE, (256, 40), center=True)
            
            if not match:
                self.draw_text_outlined("Nenhum item recuperado nesta partida.", pygame.font.SysFont("Courier New", 14, bold=True), (180,180,180), COLOR_OUTLINE, (256, 192), center=True)
            else:
                for i, item_data in enumerate(match):
                    row_item = i // 4
                    col_item = i % 4
                    bx, by = 15 + (col_item * 120), 90 + (row_item * 100)
                    
                    raw_name = item_data.get('raw_name', '')
                    name = item_data.get('name', 'Desconhecido')
                    
                    if raw_name in self.item_sprites:
                        d = self.item_sprites[raw_name]
                        scale = min(48.0/(d['w']*32), 48.0/(d['h']*32), 1.0)
                        img = pygame.transform.smoothscale(d['img'], (int(d['w']*32*scale), int(d['h']*32*scale)))
                        self.screen.blit(img, (bx + (120 - img.get_width())//2, by))
                        
                    fnt = pygame.font.SysFont("Courier New", 11 if (DYNAMIC_FONT_SIZE and ("Sphere" in name or len(name) > 12)) else 13, bold=True)
                    self.draw_text_outlined(name, fnt, COLOR_TEXT, COLOR_OUTLINE, (bx + 60, by + 60), center=True)
                    
            self.draw_text_outlined("CLIQUE em qualquer lugar para voltar à lista", pygame.font.SysFont("Verdana", 12, bold=True), (200, 200, 200), COLOR_OUTLINE, (256, 350), center=True)

    def draw_talents(self):
        self.screen.blit(self.end_bg, (0, 0)) 
        self.draw_text_outlined("TALENTOS DO PERSONAGEM", pygame.font.SysFont("Verdana", 20, bold=True), COLOR_GOLD, COLOR_OUTLINE, (256, 40), center=True)
        
        t_list = [
            ("exploracao", "Exploração de Ruínas (+50 HP Máximo)"), 
            ("arqueologo", "Auxílio Arqueólogo (Garante de 3 a 6 itens)"),
            ("martelo1", "Melhoria do Martelo 1 (-1 Dano na Parede)"), 
            ("martelo2", "Melhoria do Martelo 2 (+Área e +Dano, +4 Dano na Parede)"),
            ("evo", "Escavação Evolutiva (Dobro de chance de encontrar itens Evolutivos)"),
            ("passado", "Escavando o Passado (Dobro de chance de encontrar Fósseis)"), 
            ("conhecimento", "Conhecimento Ancestral (Dobro de chance de encontrar Tesouros)")
        ]
        
        f_tal = pygame.font.SysFont("Verdana", 11, bold=True)
        for i, (key, desc) in enumerate(t_list):
            y = 100 + i * 32
            color = (50, 220, 50) if self.talents[key] else (100, 100, 100)
            pygame.draw.rect(self.screen, color, (40, y, 16, 16))
            pygame.draw.rect(self.screen, (255,255,255), (40, y, 16, 16), 2)
            if self.talents[key]:
                pygame.draw.line(self.screen, (255,255,255), (43, y+8), (47, y+12), 2)
                pygame.draw.line(self.screen, (255,255,255), (47, y+12), (53, y+4), 2)
            self.draw_text_outlined(desc, f_tal, COLOR_TEXT, COLOR_OUTLINE, (65, y+1))
        
        self.draw_text_outlined("Pressione ESC para salvar e voltar ao Menu", pygame.font.SysFont("Verdana", 12, bold=True), (150,150,150), COLOR_OUTLINE, (256, 350), center=True)

    def draw_settings(self):
        overlay = pygame.Surface((512, 384), pygame.SRCALPHA); overlay.fill((0, 0, 0, 230)); self.screen.blit(overlay, (0, 0))
        
        titulo = "JOGO PAUSADO" if self.prev_state == "GAME" else "OPÇÕES DE ÁUDIO"
        self.draw_text_outlined(titulo, pygame.font.SysFont("Verdana", 24, bold=True), COLOR_GOLD, COLOR_OUTLINE, (256, 70), center=True)
        
        self.draw_text_outlined("VOLUME:", pygame.font.SysFont("Verdana", 14, bold=True), COLOR_TEXT, COLOR_OUTLINE, (256, 140), center=True)
        pygame.draw.rect(self.screen, (60, 60, 60), (150, 165, 200, 8))
        pygame.draw.circle(self.screen, (255, 255, 255), (int(150 + self.volume * 200), 169), 10)
        self.draw_text_outlined(f"{int(self.volume*100)}%", pygame.font.SysFont("Verdana", 14, bold=True), COLOR_TEXT, COLOR_OUTLINE, (256, 200), center=True)
        
        if self.prev_state == "GAME":
            mx, my = pygame.mouse.get_pos()
            hover_voltar = 130 <= mx <= 382 and 240 <= my <= 270
            c_voltar = COLOR_GOLD if hover_voltar else COLOR_TEXT
            pygame.draw.rect(self.screen, c_voltar, (130, 240, 252, 30), 2)
            self.draw_text_outlined("VOLTAR AO MENU PRINCIPAL", pygame.font.SysFont("Verdana", 12, bold=True), c_voltar, COLOR_OUTLINE, (256, 255), center=True)
            self.draw_text_outlined("Pressione ESC para retornar ao jogo", pygame.font.SysFont("Verdana", 11, bold=True), (150,150,150), COLOR_OUTLINE, (256, 350), center=True)
        else:
            self.draw_text_outlined("Pressione ESC para salvar e retornar ao Menu", pygame.font.SysFont("Verdana", 11, bold=True), (150,150,150), COLOR_OUTLINE, (256, 350), center=True)

    def draw_game(self):
        self.screen.blit(self.bg, (0, 0))
        for item in self.active_items:
            ix, iy = item['x']*32, item['y']*32+64
            self.screen.blit(item['img'], (ix, iy))
            if item['revealed']:
                elapsed = pygame.time.get_ticks() - item['reveal_time']
                if elapsed < 1500:
                    v = int((-math.cos(elapsed * 0.008) + 1) * 85)
                    glow = item['img'].copy()
                    glow.fill((v, v, v), special_flags=pygame.BLEND_RGB_ADD)
                    for r, c in SPECIAL_MASK_EXCEPTIONS.get(item['raw_name'], []): pygame.draw.rect(glow, (0,0,0,0), (c*32, r*32, 32, 32))
                    self.screen.blit(glow, (ix, iy))
        for rock in self.placed_rocks: self.screen.blit(rock['img'], (rock['x']*32, rock['y']*32+64))
        for r in range(10):
            for c in range(13):
                if self.grid[r][c] > 0: self.screen.blit(self.tile_images[min(self.grid[r][c]-1, 5)], (c*32, r*32+64))
        if self.ui_tools:
            self.screen.blit(pygame.transform.scale(self.ui_tools["hammer_on" if self.tool=="hammer" else "hammer_off"], (60, 90)), (437, 115))
            self.screen.blit(pygame.transform.scale(self.ui_tools["pick_on" if self.tool=="pick" else "pick_off"], (60, 90)), (437, 258))
        if self.show_hit > 0:
            self.screen.blit(self.pick_hit if self.hit_type=="pick" else self.hammer_hit, (self.hit_pos[0]-32, self.hit_pos[1]-32))
            self.show_hit -= 1
        
        pygame.draw.rect(self.screen, (20, 20, 20), (43, 36, 169, 14))
        fill = (max(0, self.wall_hp) / self.max_hp) * 165
        color = (50, 220, 50) if self.wall_hp > (self.max_hp*0.5) else (220, 220, 50) if self.wall_hp > (self.max_hp*0.2) else (220, 50, 50)
        if fill > 0: pygame.draw.rect(self.screen, color, (45, 38, fill, 10))
        if SHOW_ITEM_COUNT:
            self.draw_text_outlined(f"ITENS: {sum(1 for i in self.active_items if i['revealed'])} / {len(self.active_items)}", pygame.font.SysFont("Verdana", 12, bold=True), COLOR_TEXT, COLOR_OUTLINE, (220, 35))

        if self.game_over:
            if not self.won and not self.played_collapse:
                if "collapse" in self.snd: self.snd["collapse"].play()
                self.played_collapse = True
            self.fade_alpha = min(255, self.fade_alpha + 5)
            tmp = self.end_bg.copy(); tmp.set_alpha(self.fade_alpha); self.screen.blit(tmp, (0, 0))
            if self.fade_alpha >= 180:
                self.draw_text_outlined("ESCAVAÇÃO CONCLUÍDA" if self.won else "A PAREDE DESABOU", pygame.font.SysFont("Verdana", 26, bold=True), COLOR_GOLD, COLOR_OUTLINE, (256, 45), center=True)
                coll = [i for i in self.active_items if i['revealed']]
                for i, item in enumerate(coll):
                    row, col = i // 4, i % 4
                    bx, by = 15 + (col * 120), 90 + (row * 100)
                    scale = min(48.0/(item['w']*32), 48.0/(item['h']*32), 1.0)
                    img = pygame.transform.smoothscale(item['img'], (int(item['w']*32*scale), int(item['h']*32*scale)))
                    self.screen.blit(img, (bx + (120 - img.get_width())//2, by))
                    fnt = pygame.font.SysFont("Courier New", 11 if (DYNAMIC_FONT_SIZE and ("Sphere" in item['name'] or len(item['name']) > 12)) else 13, bold=True)
                    self.draw_text_outlined(item['name'], fnt, COLOR_TEXT, COLOR_OUTLINE, (bx + 60, by + 60), center=True)
                self.draw_text_outlined("PRESSIONE [ R ] PARA REINICIAR | [ M ] PARA O MENU", pygame.font.SysFont("Verdana", 11, bold=True), (200, 200, 200), COLOR_OUTLINE, (256, 350), center=True)

    def draw(self):
        if self.state == "MENU" or (self.state == "SETTINGS" and self.prev_state == "MENU"):
            self.draw_menu()
        elif self.state == "HISTORY":
            self.draw_history()
        elif self.state == "TALENTS":
            self.draw_talents()
        elif self.state == "GAME" or (self.state == "SETTINGS" and self.prev_state == "GAME"):
            self.draw_game()

        if self.state == "SETTINGS":
            self.draw_settings()
        
        pygame.display.flip()

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.save_game_data()
                    pygame.quit(); return
                
                if event.type == pygame.MOUSEBUTTONDOWN: 
                    self.handle_click(event.pos)
                
                if event.type == pygame.KEYDOWN:
                    if self.state == "GAME" and self.game_over:
                        if event.key == pygame.K_r: self.reset_game()
                        if event.key == pygame.K_m: self.state = "MENU"
                    
                    if event.key == pygame.K_ESCAPE:
                        if self.state == "HISTORY":
                            if self.history_detail_index is not None:
                                self.history_detail_index = None 
                            else:
                                self.state = "MENU" 
                        elif self.state == "TALENTS":
                            self.save_game_data()
                            self.state = "MENU"
                        elif self.state == "GAME":
                            self.prev_state = "GAME"
                            self.state = "SETTINGS"
                        elif self.state == "MENU":
                            self.prev_state = "MENU"
                            self.state = "SETTINGS"
                        elif self.state == "SETTINGS":
                            self.save_game_data()
                            self.state = self.prev_state 

            self.draw()
            self.clock.tick(60)

if __name__ == "__main__":
    MiningGame().run()
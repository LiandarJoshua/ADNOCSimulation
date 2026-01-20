import simpy
import pygame
import random
import math

# ---------------- CONFIG ----------------
WIDTH, HEIGHT = 1200, 650
SIM_WIDTH = 900
FPS = 60
DT = 0.1

NUM_PEOPLE = 45
BASE_SPEED = 1.1
PANIC_MULT = 1.8
SMOKE_RADIUS = 90

EXIT_POSITIONS = [(850, 120), (850, 530)]

WALLS = [
    pygame.Rect(250, 0, 30, 450),
    pygame.Rect(500, 200, 30, 450),
    pygame.Rect(100, 350, 200, 30),
]

# --------------------------------------

def dist(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

# ---------- GRAPHICS HELPERS ----------
def draw_person(surface, x, y, panic):
    body_color = (80, 150, 255) if panic < 0.4 else (255, 200, 80) if panic < 0.8 else (255, 80, 80)
    pygame.draw.circle(surface, body_color, (int(x), int(y)), 6)
    pygame.draw.circle(surface, (20, 20, 20), (int(x), int(y)), 6, 1)

def draw_fire(surface, x, y, t):
    flicker = random.randint(-2, 2)
    pygame.draw.circle(surface, (255, 80, 20), (x, y), 10 + flicker)
    pygame.draw.circle(surface, (255, 200, 50), (x, y), 6 + flicker)

def draw_smoke(surface, x, y):
    smoke = pygame.Surface((SMOKE_RADIUS*2, SMOKE_RADIUS*2), pygame.SRCALPHA)
    pygame.draw.circle(smoke, (80, 80, 80, 50), (SMOKE_RADIUS, SMOKE_RADIUS), SMOKE_RADIUS)
    surface.blit(smoke, (x-SMOKE_RADIUS, y-SMOKE_RADIUS))

# ---------- SIM CLASSES ----------
class Fire:
    def __init__(self, env):
        self.env = env
        self.cells = []
        self.active = False

    def ignite(self, x, y):
        self.active = True
        self.cells.append((x, y))
        env.process(self.spread())

    def spread(self):
        while self.active:
            yield self.env.timeout(2)
            x, y = random.choice(self.cells)
            nx = max(50, min(SIM_WIDTH-50, x+random.randint(-50,50)))
            ny = max(50, min(HEIGHT-50, y+random.randint(-50,50)))
            self.cells.append((nx, ny))

class Person:
    def __init__(self, env, x, y):
        self.env = env
        self.x, self.y = x, y
        self.speed = BASE_SPEED * random.uniform(0.8, 1.2)
        self.panic = 0
        self.evacuated = False
        env.process(self.behavior())

    def behavior(self):
        while not self.evacuated:
            yield self.env.timeout(DT)

    def update(self, fire_cells, alarm_on):
        if not alarm_on or self.evacuated:
            return

        for fx, fy in fire_cells:
            if dist((self.x, self.y), (fx, fy)) < SMOKE_RADIUS:
                self.panic = min(1, self.panic + 0.025)

        speed = self.speed * (1 + self.panic * PANIC_MULT)

        ex, ey = min(EXIT_POSITIONS, key=lambda e: dist((self.x,self.y), e))
        dx, dy = ex-self.x, ey-self.y
        d = math.hypot(dx, dy) or 1

        nx = self.x + speed*dx/d
        ny = self.y + speed*dy/d
        rect = pygame.Rect(nx-5, ny-5, 10, 10)

        for wall in WALLS:
            if wall.colliderect(rect):
                return

        self.x, self.y = nx, ny
        if dist((self.x,self.y),(ex,ey)) < 12:
            self.evacuated = True

# ---------- UI ----------
class Button:
    def __init__(self, text, y, action):
        self.rect = pygame.Rect(930, y, 240, 45)
        self.text = text
        self.action = action

    def draw(self, surf, font):
        pygame.draw.rect(surf, (50,50,50), self.rect)
        pygame.draw.rect(surf, (200,200,200), self.rect, 2)
        surf.blit(font.render(self.text, True, (255,255,255)),
                  self.rect.move(20,10))

    def click(self, pos):
        if self.rect.collidepoint(pos):
            self.action()

# ---------- INIT ----------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Top-Down Evacuation Drill Simulator")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)

env = simpy.Environment()
people = [Person(env, random.randint(50, 700), random.randint(50, 600))
          for _ in range(NUM_PEOPLE)]
fire = Fire(env)
alarm_on = False

def alarm(): 
    global alarm_on
    alarm_on = True

def start_fire():
    if not fire.active:
        fire.ignite(450, 300)

def reset():
    global env, people, fire, alarm_on
    env = simpy.Environment()
    people = [Person(env, random.randint(50, 700), random.randint(50, 600))
              for _ in range(NUM_PEOPLE)]
    fire = Fire(env)
    alarm_on = False

buttons = [
    Button("🚨 Fire Alarm", 60, alarm),
    Button("🔥 Start Fire", 120, start_fire),
    Button("🔄 Reset Drill", 180, reset),
]

# ---------- MAIN LOOP ----------
running = True
while running:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        if e.type == pygame.MOUSEBUTTONDOWN:
            for b in buttons:
                b.click(e.pos)

    env.step()
    screen.fill((25,25,25))

    # Sim area background
    pygame.draw.rect(screen, (35,35,35), (0,0,SIM_WIDTH,HEIGHT))

    # Walls
    for w in WALLS:
        pygame.draw.rect(screen, (120,120,120), w)

    # Exits
    for ex,ey in EXIT_POSITIONS:
        pygame.draw.rect(screen, (0,200,0), (ex-10, ey-20, 20, 40))

    # Fire & smoke
    for fx, fy in fire.cells:
        draw_smoke(screen, fx, fy)
        draw_fire(screen, fx, fy, pygame.time.get_ticks())

    # People
    for p in people:
        p.update(fire.cells, alarm_on)
        if not p.evacuated:
            draw_person(screen, p.x, p.y, p.panic)

    # Control panel
    pygame.draw.rect(screen, (15,15,15), (SIM_WIDTH,0,WIDTH-SIM_WIDTH,HEIGHT))
    for b in buttons:
        b.draw(screen, font)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()

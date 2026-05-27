import pygame as pgm
import random as rnd
import json
import os
import glob


pgm.init()

WIDTH = 900
HEIGHT = 700

screen = pgm.display.set_mode((WIDTH, HEIGHT))
pgm.display.set_caption('Найди пару')

WHITE = (245, 245, 245)
BLACK = (20, 20, 20)
BLUE = (80, 120, 220)
GREEN = (43, 181, 43)
RED = (220, 80, 80)
GRAY = (190, 190, 190)
DARK_GRAY = (90, 90, 90)
DARK_BLUE = (0, 128, 128)
lITE_BLUE = (64, 224, 208)
PINK = (255, 105, 180)
LITE_PINK = (255, 192, 203)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, 'img')
SOUND_DIR = os.path.join(BASE_DIR, 'sounds')
SAVE_FILE = os.path.join(BASE_DIR, 'progress.json')

FPS = 60

MODES = {
    'standard': 'Стандартная игра',
    'sounds': 'Звуки',
    'timed': 'Игра на время'
}

TIME_LIMITS = {
    'easy': {
        'start': 25,
        'minimum': 12
    },
    'medium': {
        'start': 35,
        'minimum': 18
    },
    'hard': {
        'start': 50,
        'minimum': 28
    }
}

LEVELS = {
    'easy': {
        'name': 'Лёгкий',
        'rows': 4,
        'cols': 4
    },
    'medium': {
        'name': 'Средний',
        'rows': 4,
        'cols': 5
    },
    'hard': {
        'name': 'Сложный',
        'rows': 6,
        'cols': 6
    }
}

SOUND_LEVELS = {
    'easy': {
        'name': 'Начать',
        'rows': 4,
        'cols': 5
    }
}


def default_progress():
    return {
        'games_played': 0,
        'total_pairs': 0,
        'total_mistakes': 0,
        'best_mistakes': None,
        'best_time': None,
        'history': [],
        'timed_limits': {
            'easy': 25,
            'medium': 35,
            'hard': 50
        }
    }


def load_progress():
    if not os.path.exists(SAVE_FILE):
        return default_progress()

    try:
        with open(SAVE_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except json.JSONDecodeError:
        return default_progress()

    base = default_progress()

    for key in base:
        if key not in data:
            data[key] = base[key]

    for level_key in TIME_LIMITS:
        if level_key not in data['timed_limits']:
            data['timed_limits'][level_key] = TIME_LIMITS[level_key]['start']

    return data


def save_progress(progress):
    with open(SAVE_FILE, 'w', encoding='utf-8') as file:
        json.dump(progress, file, ensure_ascii=False, indent=4)


progress = load_progress()


def format_time(seconds):
    minutes = seconds // 60
    sec = seconds % 60
    return f'{minutes:02d}:{sec:02d}'


def draw_text(text, x, y, font, color=BLACK, center=False):
    text_surface = font.render(text, True, color)

    if center:
        rect = text_surface.get_rect(center=(x, y))
        screen.blit(text_surface, rect)
    else:
        screen.blit(text_surface, (x, y))

def get_rnd_set():
        sets = [fld for fld in os.listdir(IMG_DIR)
                if os.path.isdir(os.path.join(IMG_DIR, fld))]
        if not sets:
            return None
        set = rnd.choice(sets)
        return os.path.join(IMG_DIR, set)


class Button:
    def __init__(self, x, y, w, h, text, color=DARK_BLUE):
        self.rect = pgm.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.font = pgm.font.Font('text_font.ttf', 28)

    def draw(self):
        pgm.draw.rect(screen, self.color, self.rect, border_radius=16)
        pgm.draw.rect(screen, BLACK, self.rect, 2, border_radius=16)

        text_surface = self.font.render(self.text, True, WHITE)
        text_rect = text_surface.get_rect(center=self.rect.center)

        screen.blit(text_surface, text_rect)

    def is_clicked(self, event):
        return event.type == pgm.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos)
    

class Card:
    def __init__(self, face_p, pair_id, x, y, back_p=None, size=(80, 120)):
        self.rect = pgm.Rect(x, y, size[0], size[1])

        self.face_path = face_p
        self.pair_id = pair_id

        if back_p is None:
            back_p = os.path.join(IMG_DIR, 'back.jpg')

            if not os.path.exists(back_p):
                back_p = os.path.join(IMG_DIR, 'back.JPG')

            if not os.path.exists(back_p):
                back_p = os.path.join(IMG_DIR, 'back.jpeg')

            if not os.path.exists(back_p):
                back_p = os.path.join(IMG_DIR, 'back.JPEG')

        self.back = pgm.image.load(back_p).convert_alpha()
        self.back = pgm.transform.scale(self.back, size)

        self.face = pgm.image.load(face_p).convert_alpha()
        self.face = pgm.transform.scale(self.face, size)

        self.is_face = False
        self.is_pair = False
        self.sound = None

    def appear(self, screen):
        if self.is_face or self.is_pair:
            screen.blit(self.face, self.rect.topleft)
        else:
            screen.blit(self.back, self.rect.topleft)

    def flip(self):
        if not self.is_pair:
            self.is_face = not self.is_face

    def is_chosen(self, pos):
        return self.rect.collidepoint(pos)


class Game:
    def __init__(self, mode_key, level_key):
        self.mode_key = mode_key
        self.mode_name = MODES[mode_key]

        self.level_key = level_key
        if self.mode_key == 'sounds':
            self.level = SOUND_LEVELS[level_key]
        else:
            self.level = LEVELS[level_key]

        self.rows = self.level['rows']
        self.cols = self.level['cols']

        if self.mode_key == 'sounds':
            self.set_dir = None
        else:
            self.set_dir = get_rnd_set()

            if self.set_dir is None:
                raise ValueError(
                    'В папке img нет папок с наборами картинок. '
                    'Создайте, например, img/set1 и положите туда face1.jpg, face2.jpg...'
                )

        self.font = pgm.font.Font('text_font.ttf', 42)
        self.medium_font = pgm.font.Font('text_font.ttf', 30)
        self.small_font = pgm.font.Font('text_font.ttf', 24)

        self.back = os.path.join(IMG_DIR, 'back.jpg')
        if not os.path.exists(self.back):
            self.back = os.path.join(IMG_DIR, 'back.JPG')

        if not os.path.exists(self.back):
            self.back = os.path.join(IMG_DIR, 'back.jpeg')

        if not os.path.exists(self.back):
            self.back = os.path.join(IMG_DIR, 'back.JPEG')

        if not os.path.exists(self.back):
            raise ValueError('В папке img нет нужного файла')
        
        self.koloda = self.make_koloda()

        self.comparing = []
        self.score = 0
        self.mistakes = 0

        self.waiting = False
        self.wait_start = 0

        self.game_started_at = None
        self.finished_time = None

        if self.mode_key == 'sounds':
            self.preview = False
            self.game_started_at = pgm.time.get_ticks()
        else:
            self.preview = True
            self.preview_start = pgm.time.get_ticks()
            self.preview_time = 3000

        if self.mode_key == 'timed':
            self.time_limit = progress['timed_limits'][self.level_key]
        else:
            self.time_limit = None

        self.time_is_over = False

        self.end = False
        self.result_saved = False

        self.menu_button = Button(20, 20, 130, 45, 'В меню', PINK)

    def get_needed_pairs(self):
        return self.rows * self.cols // 2

    def get_card_images(self):
        image_paths = []

        for ext in ['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG']:
            image_paths.extend(glob.glob(os.path.join(self.set_dir, f'face*.{ext}')))

        # Убираем возможные повторы одного и того же файла
        image_paths = list(set(image_paths))

        needed_pairs = self.get_needed_pairs()

        if len(image_paths) < needed_pairs:
            return None

        # Берём случайные уникальные картинки:
        # одна картинка = одна пара
        return rnd.sample(image_paths, needed_pairs)
    
    def get_sound_files(self):
        sound_paths = []

        for ext in ['wav', 'mp3', 'ogg', 'WAV', 'MP3', 'OGG']:
            sound_paths.extend(glob.glob(os.path.join(SOUND_DIR, f'sound*.{ext}')))

        sound_paths.sort()

        needed_pairs = self.get_needed_pairs()

        if len(sound_paths) < needed_pairs:
            return None

        return sound_paths[:needed_pairs]

    def make_koloda(self):
        if self.mode_key == 'sounds':
            return self.make_sound_koloda()

        images = self.get_card_images()

        if images is None:
            raise ValueError(
                'Не хватает карт для создания уровня(('
            )
        cards_data = []

        for pair_id, image_path in enumerate(images):
            cards_data.append((image_path, pair_id))
            cards_data.append((image_path, pair_id))

        rnd.shuffle(cards_data)

        koloda = []

        top_panel_height = 95
        bottom_margin = 40

        gap = 10

        available_w = WIDTH - 80
        available_h = HEIGHT - top_panel_height - bottom_margin

        card_w = int((available_w - gap * (self.cols - 1)) / self.cols)
        card_h = int((available_h - gap * (self.rows - 1)) / self.rows)

        card_w = min(card_w, 90)
        card_h = min(card_h, 110)

        start_x = (WIDTH - (card_w * self.cols + gap * (self.cols - 1))) // 2
        start_y = top_panel_height

        for index, card_data in enumerate(cards_data):
            face_path, pair_id = card_data

            row = index // self.cols
            col = index % self.cols

            x = start_x + col * (card_w + gap)
            y = start_y + row * (card_h + gap)

            card = Card(
                face_p=face_path,
                pair_id=pair_id,
                x=x,
                y=y,
                back_p=self.back,
                size=(card_w, card_h)
            )

            koloda.append(card)
                

        return koloda
    
    def make_sound_koloda(self):
        sounds = self.get_sound_files()

        if sounds is None:
            raise ValueError(
                'Не хватает карт для создания уровня(('
            )

        cards_data = []

        for pair_id, sound_path in enumerate(sounds):
            cards_data.append((pair_id, sound_path))
            cards_data.append((pair_id, sound_path))

        rnd.shuffle(cards_data)

        koloda = []

        top_panel_height = 95
        bottom_margin = 40
        gap = 10

        available_w = WIDTH - 80
        available_h = HEIGHT - top_panel_height - bottom_margin

        card_w = int((available_w - gap * (self.cols - 1)) / self.cols)
        card_h = int((available_h - gap * (self.rows - 1)) / self.rows)

        card_size = min(card_w, card_h, 100)

        card_w = card_size
        card_h = card_size

        start_x = (WIDTH - (card_w * self.cols + gap * (self.cols - 1))) // 2
        start_y = top_panel_height

        back_path = self.back

        face_path = os.path.join(IMG_DIR, 'notpickme', 'face10.jpg')

        if not os.path.exists(face_path):
            face_path = os.path.join(IMG_DIR, 'notpickme', 'face10.JPG')

        if not os.path.exists(face_path):
            face_path = os.path.join(IMG_DIR, 'notpickme', 'face10.jpeg')

        if not os.path.exists(face_path):
            face_path = os.path.join(IMG_DIR, 'notpickme', 'face10.JPEG')

        if not os.path.exists(face_path):
            raise ValueError('В папке img/notpickme нет файла face10.jpg / face10.JPG / face10.jpeg / face10.JPEG')

        for index, card_data in enumerate(cards_data):
            pair_id, sound_path = card_data

            row = index // self.cols
            col = index % self.cols

            x = start_x + col * (card_w + gap)
            y = start_y + row * (card_h + gap)

            card = Card(
                face_p=face_path,
                pair_id=pair_id,
                x=x,
                y=y,
                back_p=back_path,
                size=(card_w, card_h)
            )

            card.sound = pgm.mixer.Sound(sound_path)

            koloda.append(card)

        return koloda

    def elapsed_seconds(self):
        if self.finished_time is not None:
            return self.finished_time

        if self.game_started_at is None:
            return 0

        return (pgm.time.get_ticks() - self.game_started_at) // 1000

    def draw(self):
        screen.fill(LITE_PINK)

        self.menu_button.draw()

        title = f"{self.mode_name} — {self.level['name']}"
        draw_text(title, WIDTH // 2, 30, self.medium_font, BLACK, center=True)

        draw_text(f'Пары: {self.score}/{self.get_needed_pairs()}', 180, 55, self.small_font)
        draw_text(f'Ошибки: {self.mistakes}', 340, 55, self.small_font)

        if self.mode_key == 'timed':
            draw_text(
                f'Осталось: {format_time(self.remaining_seconds())}',
                500,
                55,
                self.small_font,
                RED
            )
        else:
            draw_text(
                f'Время: {format_time(self.elapsed_seconds())}',
                500,
                55,
                self.small_font,
                DARK_GRAY
    )       
            

        for card in self.koloda:
            if self.preview:
                screen.blit(card.face, card.rect.topleft)
            else:
                card.appear(screen)

        pgm.display.flip()

    def update_preview(self):
        if self.preview:
            current_time = pgm.time.get_ticks()

            if current_time - self.preview_start >= self.preview_time:
                self.preview = False
                self.game_started_at = pgm.time.get_ticks()

                for card in self.koloda:
                    card.is_face = False

    def handle_click(self, pos):
        if self.end or self.waiting or self.preview:
            return

        for card in self.koloda:
            if card.is_chosen(pos) and not card.is_face and not card.is_pair:
                card.flip()

                if self.mode_key == 'sounds' and card.sound is not None:
                    card.sound.play()
                

                self.comparing.append(card)

                if len(self.comparing) == 2:
                    self.check_pair()

                break

    def check_pair(self):
        first_card = self.comparing[0]
        second_card = self.comparing[1]

        if first_card.pair_id == second_card.pair_id:
            first_card.is_pair = True
            second_card.is_pair = True

            self.score += 1
            self.comparing = []

            self.check_win()
        else:
            self.mistakes += 1
            self.waiting = True
            self.wait_start = pgm.time.get_ticks()

    def update_waiting(self):
        if self.waiting:
            current_time = pgm.time.get_ticks()

            if current_time - self.wait_start > 1000:
                for card in self.comparing:
                    card.flip()

                self.comparing = []
                self.waiting = False

    def check_win(self):
        for card in self.koloda:
            if not card.is_pair:
                return

        self.end = True
        self.finished_time = self.elapsed_seconds()
        self.save_game_result()

    def remaining_seconds(self):
        if self.mode_key != 'timed':
            return None

        if self.preview:
            return self.time_limit

        elapsed = self.elapsed_seconds()
        remaining = self.time_limit - elapsed

        if remaining < 0:
            remaining = 0

        return remaining
    
    def update_timer(self):
        if self.mode_key != 'timed':
            return

        if self.preview or self.end:
            return

        if self.remaining_seconds() <= 0:
            self.time_is_over = True
            self.end = True
            self.finished_time = self.time_limit

    def save_game_result(self):
        if self.result_saved:
            return

        if self.mode_key == 'timed':
            current_limit = progress['timed_limits'][self.level_key]
            minimum_limit = TIME_LIMITS[self.level_key]['minimum']

            if current_limit > minimum_limit:
                progress['timed_limits'][self.level_key] -= 1

            save_progress(progress)
            self.result_saved = True
            return

        if self.mode_key != 'standard':
            self.result_saved = True
            return

        progress['games_played'] += 1
        progress['total_pairs'] += self.score
        progress['total_mistakes'] += self.mistakes

        if progress['best_mistakes'] is None or self.mistakes < progress['best_mistakes']:
            progress['best_mistakes'] = self.mistakes

        if progress['best_time'] is None or self.finished_time < progress['best_time']:
            progress['best_time'] = self.finished_time

        progress['history'].append({
            'level_key': self.level_key,
            'level': self.level['name'],
            'mistakes': self.mistakes,
            'time': self.finished_time
        })

        save_progress(progress)
        self.result_saved = True

font_title = pgm.font.Font('text_font.ttf', 60)
font_big = pgm.font.Font('text_font.ttf', 42)
font_medium = pgm.font.Font('text_font.ttf', 30)
font_small = pgm.font.Font('text_font.ttf', 24)

def draw_main_menu():
    screen.fill(LITE_PINK)

    draw_text('Найди пару', WIDTH // 2, 80, font_title, BLACK, center=True)

    draw_text(f"Сыграно игр: {progress['games_played']}", WIDTH // 2, 160, font_medium, BLACK, center=True)

    if progress['best_mistakes'] is None:
        mistakes_text = 'Лучший результат по ошибкам: пока нет'
    else:
        mistakes_text = f"Лучший результат по ошибкам: {progress['best_mistakes']}"

    if progress['best_time'] is None:
        time_text = 'Самое быстрое время: пока нет'
    else:
        time_text = f"Самое быстрое время: {format_time(progress['best_time'])}"

    draw_text(mistakes_text, WIDTH // 2, 205, font_small, DARK_GRAY, center=True)
    draw_text(time_text, WIDTH // 2, 235, font_small, DARK_GRAY, center=True)


def draw_mode_select(selected_mode_name):
    screen.fill(LITE_PINK)

    draw_text(selected_mode_name, WIDTH // 2, 90, font_big, BLACK, center=True)
    draw_text('Выберите уровень сложности', WIDTH // 2, 145, font_medium, DARK_GRAY, center=True)


def draw_result_screen(game):
    screen.fill(LITE_PINK)

    draw_text('Победа!', WIDTH // 2, 110, font_title, GREEN, center=True)

    draw_text(f'Режим: {game.mode_name}', WIDTH // 2, 200, font_medium, BLACK, center=True)
    draw_text(f"Сложность: {game.level['name']}", WIDTH // 2, 240, font_medium, BLACK, center=True)
    draw_text(f'Время: {format_time(game.finished_time)}', WIDTH // 2, 300, font_medium, BLACK, center=True)
    draw_text(f'Ошибки: {game.mistakes}', WIDTH // 2, 340, font_medium, BLACK, center=True)

def draw_time_over_screen(game):
    screen.fill(LITE_PINK)

    draw_text('Время вышло!', WIDTH // 2, 120, font_title, RED, center=True)

    draw_text(f'Режим: {game.mode_name}', WIDTH // 2, 210, font_medium, BLACK, center=True)
    draw_text(f"Сложность: {game.level['name']}", WIDTH // 2, 250, font_medium, BLACK, center=True)
    draw_text(f'Ошибки: {game.mistakes}', WIDTH // 2, 300, font_medium, BLACK, center=True)
    draw_text(f'Найдено пар: {game.score}/{game.get_needed_pairs()}', WIDTH // 2, 340, font_medium, BLACK, center=True)

def get_stats_by_level(level_key):
    games = []

    for item in progress['history']:
        if item.get('level_key') == level_key:
            games.append(item)

    if len(games) == 0:
        return None

    times = [game['time'] for game in games]
    mistakes = [game['mistakes'] for game in games]

    average_time = sum(times) // len(times)
    average_mistakes = round(sum(mistakes) / len(mistakes), 1)

    last_15_games = games[-15:]
    last_15_times = [game['time'] for game in last_15_games]
    average_last_15_time = sum(last_15_times) // len(last_15_times)

    progress_seconds = average_time - average_last_15_time

    return {
        'games_count': len(games),
        'best_time': min(times),
        'best_mistakes': min(mistakes),
        'average_time': average_time,
        'average_mistakes': average_mistakes,
        'average_last_15_time': average_last_15_time,
        'progress_seconds': progress_seconds
    }


def draw_stats_screen():
    screen.fill(LITE_PINK)

    draw_text('Статистика', WIDTH // 2, 55, font_title, BLACK, center=True)
    draw_text('Только стандартный режим', WIDTH // 2, 105, font_medium, DARK_GRAY, center=True)

    y = 150

    for level_key in ['easy', 'medium', 'hard']:
        level = LEVELS[level_key]
        stats = get_stats_by_level(level_key)

        draw_text(
            f"{level['name']} {level['rows']}x{level['cols']}",
            80,
            y,
            font_medium,
            BLACK
        )

        if stats is None:
            draw_text('Пока нет завершённых игр', 80, y + 35, font_small, DARK_GRAY)
            y += 140
            continue

        draw_text(f"Игр: {stats['games_count']}", 80, y + 35, font_small, BLACK)
        draw_text(f"Лучшее время: {format_time(stats['best_time'])}", 80, y + 65, font_small, BLACK)
        draw_text(f"Минимум ошибок: {stats['best_mistakes']}", 80, y + 95, font_small, BLACK)

        draw_text(f"Среднее время: {format_time(stats['average_time'])}", 460, y + 35, font_small, BLACK)
        draw_text(f"Среднее ошибок: {stats['average_mistakes']}", 460, y + 65, font_small, BLACK)
        draw_text(
            f"Среднее за последние 15: {format_time(stats['average_last_15_time'])}",
            460,
            y + 95,
            font_small,
            BLACK
        )

        if stats['progress_seconds'] > 0:
            progress_text = f"Прогресс: быстрее на {stats['progress_seconds']} сек."
            progress_color = GREEN
        elif stats['progress_seconds'] < 0:
            progress_text = f"Сейчас медленнее на {abs(stats['progress_seconds'])} сек."
            progress_color = RED
        else:
            progress_text = 'Скорость не изменилась'
            progress_color = DARK_GRAY

        draw_text(progress_text, 460, y + 125, font_small, progress_color)

        y += 155

main_buttons = [
    Button(275, 260, 350, 60, 'Стандартная игра', DARK_BLUE),
    Button(275, 335, 350, 60, 'Звуки', DARK_BLUE),
    Button(275, 410, 350, 60, 'Игра на время', DARK_BLUE),
    Button(275, 485, 350, 60, 'Статистика', GREEN)
]

level_buttons = [
    Button(275, 230, 350, 70, 'Лёгкий', GREEN),
    Button(275, 320, 350, 70, 'Средний', BLUE),
    Button(275, 410, 350, 70, 'Сложный', RED)
]

back_to_menu_button = Button(20, 20, 130, 45, 'В меню', RED)

result_menu_button = Button(220, 460, 210, 65, 'В меню', RED)
play_again_button = Button(470, 460, 230, 65, 'Сыграть заново', GREEN)

time_over_menu_button = Button(220, 460, 210, 65, 'В меню', RED)
time_over_again_button = Button(470, 460, 230, 65, 'Попробовать снова', GREEN)

error_menu_button = Button(350, 470, 200, 60, 'В меню', RED)
stats_menu_button = Button(350, 610, 200, 55, 'В меню', RED)


state = 'main_menu'
selected_mode = None
selected_level = None
current_mode = None
current_level = None
game = None
error_message = ''

clock = pgm.time.Clock()
run = True

while run:
    clock.tick(FPS)

    for event in pgm.event.get():
        if event.type == pgm.QUIT:
            save_progress(progress)
            run = False

        if state == 'main_menu':
            if main_buttons[0].is_clicked(event):
                selected_mode = 'standard'
                state = 'level_select'

            elif main_buttons[1].is_clicked(event):
                selected_mode = 'sounds'
                current_mode = 'sounds'
                current_level = 'easy'

                try:
                    game = Game(current_mode, current_level)
                    state = 'game'
                    error_message = ''
                except Exception as error:
                    error_message = str(error)
                    state = 'error'

            elif main_buttons[2].is_clicked(event):
                selected_mode = 'timed'
                state = 'level_select'

            elif main_buttons[3].is_clicked(event):
                state = 'stats'

        elif state == 'level_select':
            if back_to_menu_button.is_clicked(event):
                state = 'main_menu'

            elif level_buttons[0].is_clicked(event):
                selected_level = 'easy'

            elif level_buttons[1].is_clicked(event):
                selected_level = 'medium'

            elif level_buttons[2].is_clicked(event):
                selected_level = 'hard'

            if selected_level is not None:
                try:
                    current_mode = selected_mode
                    current_level = selected_level

                    game = Game(selected_mode, selected_level)
                    state = 'game'
                    error_message = ''
                except Exception as error:
                    error_message = str(error)
                    state = 'error'

                selected_level = None

        elif state == 'game':
            if game.menu_button.is_clicked(event):
                # Если игрок ушёл в меню до победы, прогресс не сохраняется.
                game = None
                state = 'main_menu'

            elif event.type == pgm.MOUSEBUTTONDOWN:
                game.handle_click(event.pos)

        elif state == 'result':
            if result_menu_button.is_clicked(event):
                game = None
                state = 'main_menu'

            elif play_again_button.is_clicked(event):
                game = Game(current_mode, current_level)
                state = 'game'

        elif state == 'time_over':
            if time_over_menu_button.is_clicked(event):
                game = None
                state = 'main_menu'

        elif state == 'stats':
            if stats_menu_button.is_clicked(event):
                state = 'main_menu'

            elif time_over_again_button.is_clicked(event):
                game = Game(current_mode, current_level)
                state = 'game'

        elif state == 'error':
            if error_menu_button.is_clicked(event):
                state = 'main_menu'

    if state == 'main_menu':
        draw_main_menu()

        for button in main_buttons:
            button.draw()

        pgm.display.flip()

    elif state == 'level_select':
        draw_mode_select(MODES[selected_mode])

        back_to_menu_button.draw()

        for button in level_buttons:
            button.draw()

        pgm.display.flip()

    elif state == 'game':
        game.update_preview()
        game.update_waiting()
        game.update_timer()
        game.draw()

        if game.end:
            if game.time_is_over:
                state = 'time_over'
            else:
                state = 'result'

    elif state == 'result':
        draw_result_screen(game)
        result_menu_button.draw()
        play_again_button.draw()
        pgm.display.flip()

    elif state == 'time_over':
        draw_time_over_screen(game)
        time_over_menu_button.draw()
        time_over_again_button.draw()
        pgm.display.flip()

    elif state == 'stats':
        draw_stats_screen()
        stats_menu_button.draw()
        pgm.display.flip()

    elif state == 'error':
        screen.fill(LITE_PINK)
        draw_text('Не хватает картинок((', WIDTH // 2, 170, font_big, RED, center=True)
        draw_text(error_message, WIDTH // 2, 250, font_small, BLACK, center=True)
        error_menu_button.draw()
        pgm.display.flip()

pgm.quit()
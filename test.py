import cv2
import mediapipe as mp
import pygame
import threading
import random
import time
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow logs
os.environ['GLOG_logtostderr'] = '0'     # Suppress MediaPipe logs


# Initialize MediaPipe Hand
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)

# Global variables for threading
frame = None
running = True
lock = threading.Lock()


# Webcam reader function
def video_capture_thread(cap):
    global frame, running
    while running:
        ret, new_frame = cap.read()
        if ret:
            # Flip and store the latest frame
            new_frame = cv2.flip(new_frame, 1)
            with lock:
                frame = new_frame
        time.sleep(0.01)  # Small delay to reduce CPU usage

# Hand tracking thread
hand_position = 0.5  # Normalized position (0: left, 1: right)

def hand_tracking_thread():
    global frame, running, hand_position
    while running:
        if frame is not None:
            with lock:
                current_frame = frame.copy()

            # Convert and resize frame for faster processing
            rgb_frame = cv2.cvtColor(current_frame, cv2.COLOR_BGR2RGB)
            small_frame = cv2.resize(rgb_frame, (320, 240))

            # Process the smaller frame
            results = hands.process(small_frame)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Get the x-coordinate of the wrist (rescale to full screen width)
                    wrist_x = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].x
                    hand_position = wrist_x
        time.sleep(0.03)  # Limit to ~30 FPS for hand tracking

# Pygame setup
pygame.init()
screen_width, screen_height = 800, 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Hand-Controlled Car Game")

# Load assets
road_image = pygame.image.load("road.png").convert()
road_image = pygame.transform.scale(road_image, (screen_width, screen_height))

player_car = pygame.image.load("player_car.png").convert_alpha()
player_car = pygame.transform.scale(player_car, (80, 100))

enemy_car = pygame.image.load("enemy_car.png").convert_alpha()
enemy_car = pygame.transform.scale(enemy_car, (50, 100))

# Player properties
player_width, player_height = 50, 100
player_x = screen_width // 2
player_y = screen_height - 120

# Obstacles (enemy cars)
obstacles = []
obstacle_width, obstacle_height = 50, 100
obstacle_speed = 5

# Game loop
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 36)

coin_image = pygame.image.load("coin.png").convert_alpha()
coin_image = pygame.transform.scale(coin_image, (30, 30))  # Adjust size as needed

# Coins list
coins = []
coin_width, coin_height = 30, 30
coin_speed = 5

# Update game loop to reduce redundant operation

def game_loop():
    global running, hand_position, player_x

    score = 0
    spawn_timer = 0
    coin_timer = 0
    game_running = True

    while game_running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_running = False
                running = False

        # Update player position based on hand tracking
        player_x = int(hand_position * screen_width) - player_width // 2
        player_x = max(0, min(player_x, screen_width - player_width))  # Boundary check

        # Spawn new obstacles
        spawn_timer += 1
        if spawn_timer > 60:  # Spawn every 60 frames
            spawn_timer = 0
            new_obstacle = [random.randint(0, screen_width - obstacle_width), -obstacle_height]
            obstacles.append(new_obstacle)

        # Spawn coins
        coin_timer += 1
        if coin_timer > 100:  # Spawn every 100 frames
            coin_timer = 0
            new_coin = [random.randint(0, screen_width - coin_width), -coin_height]
            coins.append(new_coin)

        # Update obstacles
        for obstacle in obstacles:
            obstacle[1] += obstacle_speed
            if obstacle[1] > screen_height:
                obstacles.remove(obstacle)
                score += 1  # Increase score for dodging an obstacle

        # Update coins
        for coin in coins[:]:
            coin[1] += coin_speed
            if coin[1] > screen_height:
                coins.remove(coin)

            # Check for coin collection
            if (
                player_x < coin[0] + coin_width
                and player_x + player_width > coin[0]
                and player_y < coin[1] + coin_height
                and player_y + player_height > coin[1]
            ):
                coins.remove(coin)
                score += 5  # Increase score for collecting a coin

        # Check for collisions
        for obstacle in obstacles:
            if (
                player_x < obstacle[0] + obstacle_width
                and player_x + player_width > obstacle[0]
                and player_y < obstacle[1] + obstacle_height
                and player_y + player_height > obstacle[1]
            ):
                game_running = False

        # Drawing
        screen.blit(road_image, (0, 0))
        screen.blit(player_car, (player_x, player_y))
        for obstacle in obstacles:
            screen.blit(enemy_car, (obstacle[0], obstacle[1]))
        for coin in coins:
            screen.blit(coin_image, (coin[0], coin[1]))

        # Display score
        score_text = font.render(f"Score: {score}", True, (255, 255, 255))
        screen.blit(score_text, (10, 10))

        pygame.display.flip()
        clock.tick(30)

# Main function remains unchanged


# Main program
def main():
    global running

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not access the webcam.")
        return

    # Start the video capture thread
    video_thread = threading.Thread(target=video_capture_thread, args=(cap,))
    video_thread.start()

    # Start the hand tracking thread
    hand_thread = threading.Thread(target=hand_tracking_thread)
    hand_thread.start()

    # Run the game loop
    try:
        game_loop()
    finally:
        running = False
        video_thread.join()
        hand_thread.join()
        cap.release()
        cv2.destroyAllWindows()
        pygame.quit()

if __name__ == "__main__":
    main()

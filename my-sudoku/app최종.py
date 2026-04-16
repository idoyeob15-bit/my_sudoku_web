import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
from sudoku import Sudoku

# 1. 경로 설정: app.py가 있는 현재 폴더를 그대로 사용합니다.
base_dir = os.path.abspath(os.path.dirname(__file__))

# template_folder를 base_dir로 설정해서 같은 폴더의 html을 찾게 합니다.
app = Flask(__name__, template_folder=base_dir)
socketio = SocketIO(app, cors_allowed_origins="*")

print(f"\n--- 서버 시작 ---")
print(f"현재 폴더 위치: {base_dir}")
print(f"HTML 파일을 찾는 곳: {base_dir}")
print(f"----------------\n")

users = {} 
rooms = {} 

@app.route('/')
def index():
    # 이제 같은 폴더에 있는 sudoku.html을 바로 부릅니다.
    return render_template('sudoku.html')

# --- 아래는 기존과 동일한 로직 ---

@socketio.on('login')
def on_login(data):
    username = data['username']
    users[username] = request.sid
    print(f"{username} 접속함")

@socketio.on('invite_player')
def on_invite(data):
    target = data['target']
    from_user = data['from_user']
    if target in users:
        emit('receive_invite', {'from': from_user}, room=users[target])

@socketio.on('accept_invite')
def on_accept(data):
    p1, p2 = data['p1'], data['p2']
    room_id = f"room_{min(p1, p2)}_{max(p1, p2)}"
    join_room(room_id)
    
    puzzle_obj = Sudoku(3).difficulty(0.5)
    board = puzzle_obj.board
    puzzle_str = "".join([str(val if val is not None else 0) for row in board for val in row])
    
    sol_board = puzzle_obj.solve().board
    solution_str = "".join([str(val) for row in sol_board for val in row])
    
    rooms[room_id] = {
        "solution": solution_str,
        "scores": {p1: 0, p2: 0}
    }
    
    emit('game_start', {'room': room_id, 'puzzle': puzzle_str}, room=room_id)

@socketio.on('check_number')
def on_check(data):
    room = data['room']
    idx = int(data['index'])
    val = data['value']
    user = data['username']
    
    if rooms[room]['solution'][idx] == val:
        rooms[room]['scores'][user] += 1
        emit('result', {'idx': idx, 'val': val, 'is_correct': True}, room=request.sid)
        emit('opponent_progress', {'user': user, 'score': rooms[room]['scores'][user]}, room=room, include_self=False)
    else:
        emit('result', {'idx': idx, 'is_correct': False}, room=request.sid)

if __name__ == '__main__':
    socketio.run(app, debug=True)
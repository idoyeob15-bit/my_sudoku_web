import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
from sudoku import Sudoku

base_dir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=base_dir)
socketio = SocketIO(app, cors_allowed_origins="*")

users = {}  # {닉네임: sid}
rooms = {}  # {방ID: 게임정보}

@app.route('/')
def index():
    return render_template('sudoku.html')

@socketio.on('login')
def on_login(data):
    username = data['username']
    users[username] = request.sid
    print(f"DEBUG: {username} 로그인")

@socketio.on('invite_player')
def on_invite(data):
    target, from_user = data['target'], data['from_user']
    if target in users:
        emit('receive_invite', {'from': from_user}, room=users[target])
    else:
        emit('error_msg', {'msg': '상대방이 접속 중이 아닙니다.'}, room=request.sid)

@socketio.on('accept_invite')
def on_accept(data):
    p1, p2 = data['p1'], data['p2'] # p1: 초대한 사람, p2: 수락한 사람
    room_id = f"room_{min(p1, p2)}_{max(p1, p2)}"
    
    # 두 사람 모두를 Socket.IO Room에 입장시킴
    if p1 in users and p2 in users:
        join_room(room_id, sid=users[p1])
        join_room(room_id, sid=users[p2])
        
        # 스도쿠 퍼즐 생성
        puzzle_obj = Sudoku(3).difficulty(0.5)
        puzzle_str = "".join([str(val if val is not None else 0) for row in puzzle_obj.board for val in row])
        sol_str = "".join([str(val) for row in puzzle_obj.solve().board for val in row])
        
        rooms[room_id] = {"solution": sol_str}
        
        # 중요: 방에 있는 모든 사람(p1, p2)에게 게임 시작 신호와 퍼즐 데이터 전송
        emit('game_start', {'room': room_id, 'puzzle': puzzle_str}, room=room_id)
        print(f"DEBUG: {p1}와 {p2}의 게임 시작")

@socketio.on('check_number')
def on_check(data):
    room, idx, val, user = data['room'], int(data['index']), data['value'], data['username']
    if room in rooms and rooms[room]['solution'][idx] == val:
        emit('result', {'idx': idx, 'val': val, 'is_correct': True}, room=request.sid)
        emit('opponent_progress', {'user': user}, room=room, include_self=False)
    else:
        emit('result', {'idx': idx, 'is_correct': False}, room=request.sid)

@socketio.on('game_over')
def on_game_over(data):
    emit('opponent_eliminated', {'loser': data['username']}, room=data['room'], include_self=False)

if __name__ == '__main__':
    socketio.run(app, debug=True)
from fastapi import FastAPI
from fastapi_utils.tasks import repeat_every
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
from collections import deque
import logging
from fastapi.testclient import TestClient

app = FastAPI()

logger = logging.getLogger(__name__)

class userQueue():
    def __init__(self):
        self.queue = deque()

    def push(self, item):
        self.queue.append(item)

    def pop(self):
        if len(self.queue) > 0:
            return self.queue.popleft()
        else:
            return None
    
    def getLen(self):
        return len(self.queue)

class Lobby():
    waitingPlayers = userQueue()
    def __init__(self):
        self.slotOne = ""
        self.slotTwo = ""

    def finishGame(self):
        if self.slotOne != "":
            if self.slotTwo != "":
                self.slotOne = ""
                self.slotTwo = ""

    def fillSlot(self, input):
        if self.slotOne == "":
            self.slotOne = input
            return "Successfully filled Slot One"
        elif self.slotTwo == "":
            self.slotTwo = ""
            return "Successfully filled Slot Two"
        else:
            return "Slots Full"

def attemptMatchmaking(inputLobby):
    numMatchmaked = 0
    if inputLobby.waitingPlayers.getLen() > 0:
        if inputLobby.slotOne == "":
            inputLobby.slotOne = inputLobby.waitingPlayers.pop()
            numMatchmaked += 1
    if inputLobby.waitingPlayers.getLen() > 0:
        if inputLobby.slotTwo == "":
            inputLobby.slotTwo = inputLobby.waitingPlayers.pop()
            numMatchmaked += 1
    return numMatchmaked

gameLobby = Lobby()
Lobby.waitingPlayers.push("Player1")
Lobby.waitingPlayers.push("Player2")
Lobby.waitingPlayers.push("Player3")
Lobby.waitingPlayers.push("Player4")
Lobby.waitingPlayers.push("Player5")
Lobby.waitingPlayers.push("Player6")

@app.get("/")
async def root():
    return {"message": "Lobby Created\n"}

@app.on_event("startup")
@repeat_every(seconds=45, logger=logger)
async def finishMatchForLobby1():
    gameLobby1.finishGame() 
    print("Finished Game For Lobby 1\n")

@app.on_event("startup")
@repeat_every(seconds=38, logger=logger)
async def finishMatchForLobby2():
    gameLobby2.finishGame() 
    print("Finished Game for Lobby 2\n")

@app.on_event("startup")
@repeat_every(seconds=10, logger=logger)
async def attemptToMatchmake():
    output1 = attemptMatchmaking(gameLobby1) 
    output2 = attemptMatchmaking(gameLobby2)
    print("Matchmaked", output1, "players for Lobby1\n")
    print("Matchmaked", output2, "players for Lobby2\n")


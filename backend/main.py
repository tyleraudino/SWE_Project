import datetime
from typing import Optional, Annotated
import logging
import argon2
import jwt
import motor.motor_asyncio
from bson import ObjectId
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.utils import get_authorization_scheme_param
from pydantic import BaseModel, Field, ConfigDict

ph = argon2.PasswordHasher()
app = FastAPI()

# todo - secret key should be stored in environment variable
SECRET_KEY = "76b33515ec3f0b4a1f30cb3f78e0aaa880662251c07144fc69b18442974ff221"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # to put frontend url
    allow_credentials=True,
    allow_methods=["*"],  # allows GET, POST, OPTIONS, etc.
    allow_headers=["*"],  # allows all headers
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# mongo connection
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/")
db = client["your_database"]
user_collection = db["user_collection"]
collection = db["your_collection"]

# pydantic models
# ---------------

# for item data

class Item(BaseModel):
    name: str
    description: str



# for goal data
class Goal(BaseModel):
    title: str
    description: str
    points: int
    user_id: str = None
    recurrence: str
    lastCompleted: Optional[str]


# to store rewards
class Reward(BaseModel):
    image_path: str
    unlocked: bool
    user_id: str = None


# to update rewards
class UpdateReward(BaseModel):
    unlocked: bool
    user_id: str = None


# for user login data
class UserLogin(BaseModel):
    username: str
    password: str


# for user registration
class UserRegister(UserLogin):
    email: str
    first_name: str
    last_name: str


# for updating password
class UpdatePassword(BaseModel):
    password: str


class UpdateEmail(BaseModel):
    email: str


class UpdateUsername(BaseModel):
    username: str


class UpdatePoints(BaseModel):
    points: int


# for user token
class UserToken(BaseModel):
    object_id: str
    expires_in: datetime.datetime


# for updating goals
class UpdateGoal(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    points: Optional[int] = None
    user_id: Optional[str] = None
    recurrence: Optional[str] = None
    lastCompleted: Optional[str] = None



def generate_jwt(object_id: ObjectId) -> str:
    to_encode = {
        "object_id": str(object_id),
        "expires_in": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).isoformat()
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# from fastapi itself
async def oauth2_scheme(request: Request) -> Optional[str]:
    authorization = request.headers.get("Authorization")
    scheme, param = get_authorization_scheme_param(authorization)
    if not authorization or scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return param
    

def decode_jwt(token: Annotated[str, Depends(oauth2_scheme)]) -> UserToken:
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return UserToken.model_validate(decoded_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# use this whenever you want to get the current user
UserDep = Annotated[UserToken, Depends(decode_jwt)]


# registers user
@app.post("/user/register")
async def register_user(user: UserRegister):
    if await user_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="User already registered")

    user_data = user.model_dump()
    user_data["password"] = ph.hash(user_data["password"])
    user_data["points"] = 0
    result = await user_collection.insert_one(user_data)
    if result.inserted_id:
        return {
            "message": "User registered successfully!",
            "token": generate_jwt(result.inserted_id)
        }
    else:
        raise HTTPException(status_code=400, detail="User registration failed")


# login user
@app.post("/user/login")
async def login_user(user: UserLogin):
    user_data = await user_collection.find_one({"username": user.username})
    if not user_data:
        raise HTTPException(status_code=400, detail="User not found")
    
    try:
        if not ph.verify(user_data["password"], user.password):
            raise HTTPException(status_code=400, detail="Invalid password")
    except argon2.exceptions.VerifyMismatchError:
        raise HTTPException(status_code=400, detail="Invalid password")
    
    if ph.check_needs_rehash(user_data["password"]):
        user_data["password"] = ph.hash(user.password)
        await user_collection.update_one({"_id": user_data["_id"]}, {"$set": {"password": user_data["password"]}})
    
    return {
        "message": "Login successful!",
        "email": user_data["email"],
        "first_name": user_data["first_name"],
        "last_name": user_data["last_name"],
        "points": user_data["points"],
        "token": generate_jwt(user_data["_id"])
    }


# change password
@app.post("/user/change_password")
async def change_password(user: UserDep, data: UpdatePassword):
    user_data = await user_collection.find_one({"_id": ObjectId(user.object_id)})
    if not user_data:
        raise HTTPException(status_code=400, detail="User not found")
    
    user_data["password"] = ph.hash(data.password)
    await user_collection.update_one({"_id": user_data["_id"]}, {"$set": {"password": user_data["password"]}})
    return {"message": "Password changed successfully!"}


# change email
@app.post("/user/change_email")
async def change_email(user: UserDep, data: UpdateEmail):
    user_data = await user_collection.find_one({"_id": ObjectId(user.object_id)})
    if not user_data:
        raise HTTPException(status_code=400, detail="User not found")
    
    await user_collection.update_one({"_id": user_data["_id"]}, {"$set": {"email": data.email}})
    return {"message": "Email changed successfully!"}


# change username
@app.post("/user/change_username")
async def change_username(user: UserDep, data: UpdateUsername):
    user_data = await user_collection.find_one({"_id": ObjectId(user.object_id)})
    if not user_data:
        raise HTTPException(status_code=400, detail="User not found")
    
    if await user_collection.find_one({"username": data.username}):
        raise HTTPException(status_code=403, detail="Username already taken")
    
    await user_collection.update_one({"_id": user_data["_id"]}, {"$set": {"username": data.username}})
    return {"message": "User ID changed successfully!"}


# change points
@app.post("/user/change_points")
async def change_points(user: UserDep, data: UpdatePoints):
    user_data = await user_collection.find_one({"_id": ObjectId(user.object_id)})
    if not user_data:
        raise HTTPException(status_code=400, detail="User not found")
    
    await user_collection.update_one({"_id": user_data["_id"]}, {"$set": {"points": data.points}})
    return {"message": "Points changed successfully!"}


# delete user
@app.delete("/user/delete")
async def delete_user(user: UserDep):
    user_data = await user_collection.find_one({"_id": ObjectId(user.object_id)})
    if not user_data:
        raise HTTPException(status_code=400, detail="User not found")
    
    await user_collection.delete_one({"_id": user_data["_id"]})
    return {"message": "User deleted successfully!"}


# get request to fetch all goals
@app.get("/goals/")
async def get_goals(user: UserDep):
    goals = []
    cursor = collection.find({"user_id": user.object_id})
    async for document in cursor:
        # Convert ObjectId to string for JSON serialization
        document['_id'] = str(document['_id'])
        goals.append(document)
    return goals

# post request to add data
@app.post("/data")
async def post_data(item: Item):
    new_data = item.dict()
    result = await collection.insert_one(new_data)
    if result.inserted_id:
        return {"message": "Data inserted successfully!"}
    else:
        raise HTTPException(status_code=400, detail="Data insertion failed")


# post request to create a goal
@app.post("/goals/")
async def create_goal(user: UserDep, goal: Goal):
    new_goal = goal.dict()
    new_goal['user_id'] = user.object_id  
    result = await collection.insert_one(new_goal)
    if result.inserted_id:
        return {"message": "Goal created successfully!", "goal_id": str(result.inserted_id)}
    else:
        raise HTTPException(status_code=400, detail="Goal creation failed")
    

# post request to delete a goal
@app.delete("/goals/{goal_id}")
async def delete_goal(user: UserDep, goal_id: str):
    try:
        object_id = ObjectId(goal_id) # converts goal_id to MongoDB's ObjectID
        print(f"Converted goal_id to ObjectId: {object_id}")
    except Exception as e:
        print(f"Invalid ObjectId for goal_id: {goal_id}, error: {e}")
        raise HTTPException(status_code=400, detail="Invalid goal ID format")
    # attempts to delete the document by ID
    result = await collection.delete_one({"_id": object_id})
    print(f"Deletion result for goal_id {goal_id}: {result.deleted_count}")
    if result.deleted_count == 1:
        return {"message": "Goal deleted successfully!"} # expected result
    else:
        raise HTTPException(status_code=404, detail="Goal not found.")
    

# request to modify goals
@app.put("/goals/{goal_id}")
async def update_goal(user: UserDep, goal_id: str, goal: UpdateGoal):
    try:
        object_id = ObjectId(goal_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid goal ID format")

    # First, verify the goal belongs to the user
    existing_goal = await collection.find_one({"_id": object_id, "user_id": user.object_id})
    if not existing_goal:
        raise HTTPException(status_code=404, detail="Goal unauthorized")

    # Create dictionary of updates, excluding None values
    updated_data = {k: v for k, v in goal.dict().items() if v is not None}

    if updated_data:
        logger.debug(f"Updating goal with data: {updated_data}")
        result = await collection.update_one(
            {"_id": object_id, "user_id": user.object_id}, 
            {"$set": updated_data} 
        )
        logger.debug(f"Update operation result: {result.raw_result}")
        if result.modified_count == 1:
            return {"message": "Goal updated successfully!"}
        else:
            raise HTTPException(status_code=404, detail="Goal not found or no changes made")
    else:
        raise HTTPException(status_code=400, detail="No valid fields provided for update")
    

# pre-defined rewards stored in the database
@app.on_event("startup")
async def populate_rewards():
    # check if rewards collection exists
    if await db["rewards"].count_documents({}) == 0:
        predefined_rewards = [
            {"rewardcat1": "/assets/rewardcat1.png", "unlocked": False},
            {"rewardcat2": "/assets/rewardcat2.png", "unlocked": False},
            {"rewardcat3": "/assets/rewardcat3.png", "unlocked": False},
            {"rewardcat4": "/assets/rewardcat4.png", "unlocked": False},
            {"rewardcat5": "/assets/rewardcat5.png", "unlocked": False},
            {"rewardcat6": "/assets/rewardcat6.png", "unlocked": False},
            {"rewardcat7": "/assets/rewardcat7.png", "unlocked": False},
            {"rewardcat8": "/assets/rewardcat8.png", "unlocked": False},
            {"rewardcat9": "/assets/rewardcat9.png", "unlocked": False},
        ]
        await db["rewards"].insert_many(predefined_rewards)


@app.put("/rewards/{reward_id}")
async def toggle_reward_unlocked(reward_id: str, user: UserDep):
    try:
        object_id = ObjectId(reward_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid reward ID format")

    # find reward
    reward = await db["rewards"].find_one({"_id": object_id})
    if not reward:
        raise HTTPException(status_code=404, detail="Reward not found")

    # toggle 'unlocked' to True
    updated = await db["rewards"].update_one(
        {"_id": object_id},
        {"$set": {"unlocked": True}}
    )

    if updated.modified_count == 1:
        return {"message": f"Reward {reward_id} unlocked successfully!"}
    else:
        raise HTTPException(status_code=500, detail="Failed to update reward")
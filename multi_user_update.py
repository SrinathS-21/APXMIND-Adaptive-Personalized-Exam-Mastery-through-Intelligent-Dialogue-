import re

# 1. Update models.py
models_path = 'src/apxmind/db/models.py'
with open(models_path, 'r') as f:
    m_content = f.read()
# Make name unique
m_content = m_content.replace(
    'name = Column(String(100), nullable=False)',
    'name = Column(String(100), unique=True, nullable=False, index=True)'
)
with open(models_path, 'w') as f:
    f.write(m_content)

# 2. Update schemas.py
schemas_path = 'src/apxmind/api/schemas.py'
with open(schemas_path, 'r') as f:
    s_content = f.read()

# Add password field to OfflineProfileRequest so they can set a password during profile setup
if 'password: str' not in s_content.split('class OfflineProfileRequest')[1].split('class')[0]:
    s_content = s_content.replace(
        'name: str = Field(..., min_length=1, max_length=100)',
        'name: str = Field(..., min_length=1, max_length=100)\n    password: str = Field(..., min_length=4)'
    )

# Change LoginRequest from email to username
s_content = s_content.replace(
    'class LoginRequest(BaseModel):\n    email: str\n    password: str',
    'class LoginRequest(BaseModel):\n    name: str\n    password: str'
)

# Add LocalUser schemas
local_user_classes = '''
class LocalUserDropdown(BaseModel):
    id: int
    name: str

class LocalDropdownResponse(BaseModel):
    success: bool = True
    users: List[LocalUserDropdown]
'''
if 'LocalDropdownResponse' not in s_content:
    s_content = s_content + '\n' + local_user_classes

with open(schemas_path, 'w') as f:
    f.write(s_content)

print("Updated models.py and schemas.py")

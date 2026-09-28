from openai import OpenAI

with open("app_cloud.py", "r") as f:
    for line in f:
        if "GROQ_API_KEY" in line and "=" in line:
            key = line.split('"')[1]
            break

print("Testing key...")

client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=key)

try:
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": "Say OK"}]
    )
    print("SUCCESS:", response.choices[0].message.content)
except Exception as e:
    print("FAILED:", str(e)[:200])

import time


outputNum = 100

def getIdentity(identityPath):  
    with open(identityPath, "r", encoding="utf-8") as f:
        
        identityContext = f.read()
    return f"role: user, content: {identityContext}"
def saveIdentity(identityPath,text):  
    with open(identityPath, "w", encoding="utf-8") as f:
        timestamp = time.asctime()
        f.writelines(f"ข้อมูลการตอบย้อนหลัง: [Answer time::{timestamp}] -> [{text}]")
        
    
    
def getPrompt():
    
    total_len = 0
    prompt = []
    prompt.append(getIdentity("characterConfig/Pina/identity.txt"))
    prompt.append(f"Below is conversation history.")
    prompt.append(getIdentity("characterConfig/Pina/chatdata.txt"))

    
    
   

    prompt.append(
        
        f"role: system, content: Here is the latest conversation.*Make sure your response is within {outputNum} characters!",
        
    )
    
    
    

    total_len = len(prompt)
    
    while total_len > 4000:
        try:
            # print(total_len)
            # print(len(prompt))
            prompt.pop(2)
            total_len = len(prompt)
        except:
            print("Error: Prompt too long!")

    # total_characters = sum(len(d['content']) for d in prompt)
    # print(f"Total characters: {total_characters}")

    return prompt

if __name__ == "__main__":
    prompt = getPrompt()
    print(prompt)
    print(len(prompt))
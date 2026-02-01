import ollama
import sys
import time
import datetime
import dotenv
from memory import cortex
from modules import realtime, actions, browser, remote, voice

# Configuration
dotenv.load_dotenv()
MODEL_NAME = "deepseek-r1:1.5b"
MEMORY_LIMIT = 20

class SparkCore:
    def __init__(self):
        self.context = []
        cortex.init_db()
        print("\n" + "="*50)
        print(f"⚡ S.P.A.R.K. Core Initialized")
        print(f"🧠 Model: {MODEL_NAME}")
        print("="*50 + "\n")
        
        # Announce startup
        voice.voice.speak("System online. Hello Sir.")
        
        # Load System Prompt
        self.update_system_prompt()

    def update_system_prompt(self):
        facts = cortex.get_all_facts()
        facts_str = "\n".join([f"- {k}: {v}" for k, v in facts.items()])
        
        system_prompt = f"""
You are S.P.A.R.K. (Sophisticated Programmable AI Research Kernel).
Current Date: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Known Facts:
{facts_str}

Protocol:
1. To remember a fact: `SAVE_FACT: key | value`
2. To log a memory: `LOG_MEMORY: content`
3. To search the web: `SEARCH: query`
4. To visit a website: `BROWSE: url` (Use this to read documentation or pages)
5. To execute system commands (files, moves, ls): `EXECUTE_CMD: command`
6. To run Python code (complex logic, math, file ops): 
   `EXECUTE_PYTHON: code`
   (Write the code on a single line or ensure the parser can handle it. For multi-line, use semicolons or ensure the system handles your output format.)
7. To access remote systems: `REMOTE_CHECK: target`
8. To speak out loud (IMPORTANT): `SPEAK: text`
   (If you want to say something to the user, typically just output text. But if you want to explicitly enforce TTS, use this. Currently, the system TTSs all final answers automatically.)

   Example: 
   EXECUTE_CMD: dir
   EXECUTE_PYTHON: import os; print(os.getcwd())

9. Always answer the user's question directly after performing any actions.
        """
        new_context = [{'role': 'system', 'content': system_prompt}]
        for msg in self.context:
            if msg['role'] != 'system':
                new_context.append(msg)
        self.context = new_context


    def add_to_memory(self, role, content):
        self.context.append({'role': role, 'content': content})
        if len(self.context) > MEMORY_LIMIT:
             self.context = [self.context[0]] + self.context[-(MEMORY_LIMIT-1):]

    def process_actions(self, response_text):
        """Parses the AI output for tool calls."""
        lines = response_text.split('\n')
        
        for i, line in enumerate(lines):
            # Clean up line
            line = line.strip()
            
            if "SAVE_FACT:" in line:
                try:
                    _, data = line.split("SAVE_FACT:", 1)
                    key, value = data.split("|", 1)
                    cortex.save_fact(key.strip(), value.strip())
                    print(f"✅ [Memory] Saved: {key.strip()} = {value.strip()}")
                except ValueError:
                    print("❌ [Memory] Error parsing SAVE_FACT")
            
            elif "LOG_MEMORY:" in line:
                _, content = line.split("LOG_MEMORY:", 1)
                cortex.save_memory(content.strip())
            
            elif "SEARCH:" in line:
                _, query = line.split("SEARCH:", 1)
                result = realtime.search_web(query.strip())
                print(f"\n🌐 [Search] Found: {result[:100]}...")
                self.add_to_memory('system', f"Search Result: {result}")
            
            elif "BROWSE:" in line:
                _, url = line.split("BROWSE:", 1)
                eye = browser.BrowserEye()
                result = eye.visit(url.strip())
                self.add_to_memory('system', f"Browser Result: {result}")

            elif "EXECUTE_CMD:" in line:
                _, cmd = line.split("EXECUTE_CMD:", 1)
                output = actions.hands.execute_command(cmd.strip())
                self.add_to_memory('system', f"Command Output: {output}")
            
            elif "EXECUTE_PYTHON:" in line:
                _, code = line.split("EXECUTE_PYTHON:", 1)
                output = actions.hands.execute_python(code.strip())
                self.add_to_memory('system', f"Python Execution Output: {output}")
                
            elif "SPEAK:" in line:
                _, text = line.split("SPEAK:", 1)
                voice.voice.speak(text.strip())


    def think(self, user_input):
        self.add_to_memory('user', user_input)
        self.update_system_prompt() 
        
        print("\n🤔 Thinking...", end="", flush=True)
        
        full_response = ""
        try:
            stream = ollama.chat(model=MODEL_NAME, messages=self.context, stream=True)
            print("\r", end="") 
            
            in_think_block = False
            for chunk in stream:
                content = chunk['message']['content']
                full_response += content
                
                if '<think>' in content:
                    in_think_block = True
                    print("\n[Internal Monologue] ----------------- \n", end="")
                    content = content.replace('<think>', '')
                
                if '</think>' in content:
                    in_think_block = False
                    print("\n------------------------------------- [Answer]: \n", end="")
                    content = content.replace('</think>', '')

                print(content, end="", flush=True)
            
            print("\n")
            
            self.process_actions(full_response)
            self.add_to_memory('assistant', full_response)
            
            # Speak the final answer if it's not too long and no specific SPEAK command was issued
            # Simple heuristic: speak the whole thing if < 200 chars, or just the first sentence?
            # For now, let's speak everything that isn't a thought or action.
            # Clean response for speech:
            speech_text = full_response
            if '<think>' in speech_text: # Handle edge cases where tags remain
                 speech_text = speech_text.split('</think>')[-1]
            
            # Remove action lines
            clean_speech = []
            for line in speech_text.split('\n'):
                if not any(x in line for x in ["SAVE_FACT:", "LOG_MEMORY:", "SEARCH:", "BROWSE:", "EXECUTE_CMD:", "EXECUTE_PYTHON:", "SPEAK:"]):
                    clean_speech.append(line)
            
            final_speech = " ".join(clean_speech).strip()
            if final_speech:
                voice.voice.speak(final_speech)
            
        except Exception as e:
            print(f"\n❌ Error: {e}")

    def run(self):
        print("Type 'exit' to shutdown. Press ENTER without typing to toggle Voice Mode.")
        while True:
            try:
                user_input = input("root@spark:~$ ")
                
                if user_input.lower() in ['exit', 'quit']:
                    break
                
                # Voice Mode Toggle
                if not user_input.strip():
                    voice.voice.speak("Listening.")
                    voice_cmd = voice.voice.listen()
                    if voice_cmd:
                        user_input = voice_cmd
                    else:
                        voice.voice.speak("I didn't catch that.")
                        continue
                
                self.think(user_input)
            except KeyboardInterrupt:
                print("\nForce Shutdown.")
                break
            except EOFError:
                break

if __name__ == "__main__":
    bot = SparkCore()
    bot.run()

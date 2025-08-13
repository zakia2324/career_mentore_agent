import os
from dotenv import load_dotenv
from typing import cast
import chainlit as cl
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, handoff
from agents.run import RunConfig, RunContextWrapper

# Load the environment variables from the .env file
load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")

# Check if the API key is present; if not, raise an error
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY is not set. Please ensure it is defined in your .env file.")

# Define the on_handoff callback function





@cl.on_chat_start
async def start():
    external_client = AsyncOpenAI(
        api_key=os.getenv("GEMINI_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    model = OpenAIChatCompletionsModel(
        model="gemini-2.5-flash-lite-preview-06-17",
        openai_client=external_client
    )

    config = RunConfig(
        model=model,
        model_provider=external_client,
        tracing_disabled=True
    )


    def on_handoff(agent: Agent, ctx: RunContextWrapper[None]):
        agent_name = agent.name
        print("--------------------------------")
        print(f"Handing off to {agent_name}...")
        print("--------------------------------")
        # Send a more visible message in the chat
        cl.Message(
            content=f"🔄 **Handing off to {agent_name}...**\n\nI'm transferring your request to our {agent_name.lower()} who will be able to better assist you.",
            author="System"
        ).send()

    
    career_agent = Agent(name="Career Agent", instructions="You are a career agent.you will suggest fields to the users", model=model,tools=[])
    job_agent= Agent(name="Job Agent", instructions="You are a job searching agent.you will find best real world jobs for the users ", model=model,tools=[])

    # Correct on_handoff function definition
    

    agent = Agent(
        name="Triage Agent",
        instructions="You are a triage agent",
        model=model,
        handoffs=[
            handoff(career_agent, on_handoff=lambda ctx: on_handoff(career_agent, ctx)),
            handoff(job_agent, on_handoff=lambda ctx: on_handoff(job_agent, ctx))
        ]
    )

    # Set session variables
    cl.user_session.set("agent", agent)
    cl.user_session.set("config", config)
    cl.user_session.set("career_agent", career_agent)
    cl.user_session.set("job_agent", job_agent)
    cl.user_session.set("chat_history", [])

    await cl.Message(content="Hello I am your career mentore agent...you may ask anything regarding career.. ?").send()


@cl.on_message
async def main(message: cl.Message):
    """Process incoming messages and generate responses."""

    
    # Send a thinking message
    msg = cl.Message(content="Thinking...")
    await msg.send()

    agent: Agent = cast(Agent, cl.user_session.get("agent"))
    config: RunConfig = cast(RunConfig, cl.user_session.get("config"))

    # Retrieve the chat history from the session.
    history = cl.user_session.get("chat_history") or []

    # Append the user's message to the history.
    history.append({"role": "user", "content": message.content})

    # Check if the message is about flight booking and trigger handoff
    if any(word in message.content.lower() for word in ["career", "suggest career", "suggest career", "find best career", "find career"]):
        career_agent = cl.user_session.get("career_agent")
        if career_agent:
            def on_handoff(agent, ctx):
                agent_name = agent.name
                print("--------------------------------")
                print(f"Handing off to {agent_name}...")
                print("--------------------------------")
                cl.Message(
                    content=f"🔄 **Handing off to {agent_name}...**\n\nI'm transferring your request to our {agent_name.lower()} who will be able to better assist you.",
                    author="System"
                ).send()
            on_handoff(career_agent, None)
            cl.user_session.set("agent", career_agent)
            msg.content = "You are now being transferred to the Career Agent. Please continue with your career agent to find better career."
            await msg.update()
            return

    # Check if the message is about destination suggestion and trigger handoff
    if any(word in message.content.lower() for word in ["job", "suggest job", "find the best real world job", "search job and show", "find the job", "linkeIn job", "indeed job", "internet job"]):
        job_agent = cl.user_session.get("job_agent")
        if job_agent:
            def on_handoff(agent, ctx):
                agent_name = agent.name
                print("--------------------------------")
                print(f"Handing off to {agent_name}...")
                print("--------------------------------")
                cl.Message(
                    content=f"🔄 **Handing off to {agent_name}...**\n\nI'm transferring your request to our {agent_name.lower()} who will be able to better assist you.",
                    author="System"
                ).send()
            on_handoff(job_agent, None)
            cl.user_session.set("agent", job_agent)
            msg.content = "You are now being transferred to the job Agent. Please continue with your job agent to find best job for you ."
            await msg.update()
            return

    try:
        result = Runner.run_sync(agent, history, run_config=config)

        response_content = result.final_output

        # Update the thinking message with the actual response
        msg.content = response_content
        await msg.update()

        # IMPORTANT FIX HERE: use "developer" instead of "assistant"
        history.append({"role": "developer", "content": response_content})

        # Update session history
        cl.user_session.set("chat_history", history)
        print(f"History: {history}")

    except Exception as e:
        msg.content = f"Error: {str(e)}"
        await msg.update()
        print(f"Error: {str(e)}")

#         def main():
#                       print("Hello from career-mentore!")


# if __name__ == "__main__":
#     main()
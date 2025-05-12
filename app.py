from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from subprocess import run
import requests
import json
import os
import logging
import asyncio

app = FastAPI()

# Response format for LLM
response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "task_runner",
        "schema": {
            "type": "object",
            "required": ["python_dependencies", "python_code"],
            "properties": {
                "python_code": {
                    "type": "string",
                    "description": "Python code to perform the task."
                },
                "python_dependencies": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "module": {
                                "type": "string",
                                "description": "Name of Python module"
                            }
                        },
                        "required": ["module"],
                        "additionalProperties": False
                    }
                }
            }
        }
    }
}

# Primary prompt for LLM
primary_prompt = """
You are an automated agent responsible for generating Python code to perform specified tasks. 
Assume 'uv' and Python are preinstalled, and your code will be executed inside a Docker container.

### Key Instructions:
1. **Output Format**: Ensure that the output is **precisely formatted** as per the task requirements, or it will be considered incorrect. Pay attention to whitespace, indentation, and formatting.
2. **Package Installation**: If a task requires any Python package installation, provide a list of those packages in the response.
3. **Execution Command**: Use `'uv run {script_name} arguments'` to execute scripts when necessary.
4. **Error Handling**: Anticipate and handle potential errors (e.g., file not found, parsing errors) gracefully in the code.
5. **Edge Cases**: Account for edge cases such as empty files, unexpected formats, or invalid data.

### Expected Response Format:
Respond with a JSON object containing:
- `python_code`: A string containing valid Python code to perform the task.
- `python_dependencies`: A list of Python packages (if any) required to complete the task.

### Task-Specific Guidelines:

#### 0. Most Important Task
- The task that asks to run a script from a URL is the most important task because if it is not executed, the rest will not get executed.
- The task will look like this: "Install `uv` (if required) and run the script `url`".
- Follow these steps to ensure the task is executed correctly:

##### Steps to Execute the Task:
1. **Check for `uv` Installation**:
   - Verify if `uv` is already installed.
   - If not installed, install `uv` using the appropriate package manager.

2. **Download the Script**:
   - Download the script from the provided URL.
   - Ensure the script is saved with the correct filename.

3. **Run the Script**:
   - Use the command `uv run {script_name} arguments` to execute the downloaded script.
   - Pass any required arguments to the script as specified in the task.

4. **Error Handling**:
   - Anticipate and handle potential errors (e.g., network issues, file not found, parsing errors) gracefully in the code.
   - Log any errors encountered during the execution.

5. **Output**:
   - Ensure the output of the script execution is captured and returned correctly.
   - If the script execution fails, provide detailed error messages to help diagnose the issue.

#### 1. Formatting Markdown
- Use `prettier@3.4.2` to format the file in-place.
- Ensure that extra spaces and trailing whitespace are removed.
- Example Expected Output:
  - The Markdown file should be formatted consistently with proper indentation, spacing, and line breaks.
- Example:
#Unformatted Markdown

This is a sample paragraph with extra spaces and trailing whitespace.

- First item
- Second item
  +Third item


    *    Fourth item

```py
print("user@example.com")

```

#### 2. Counting Wednesdays
- Parse dates in multiple formats (e.g., `DD-MMM-YYYY`, `YYYY-MM-DD`, `YYYY/MM/DD HH:mm:ss`, etc.).
- Count how many of the provided dates fall on a Wednesday.
- Write just the number to the specified output path.

#### 3. Sorting Contacts
- Sort a list of contacts by `last_name`, and then by `first_name` in case of ties.
- Ensure the output JSON is formatted precisely with correct indentation and no extra whitespace.

#### 4. Extracting First Lines from `.log` Files
- List all `.log` files in a given directory, sorted by modification time (most recent first).
- Extract the first line from each file and write it to the specified output path.
- Ensure there are no extra newline characters in the output.

#### 5. Markdown Indexing
- Extract the first H1 (`# `) from each Markdown file in a given directory.
- Create an index mapping filenames (without their directory prefix) to their titles.
- Write this mapping as a JSON object to an output file.
- if the file 'abc.md' is in folder 'xyz' then the key should be xyz/abc.md not just abc.md 

#### 6. Extracting Email Address
- Extract only the sender's email address from an email message.
- Write just the email address (without quotes) to the specified output file.
- The email should be carefully analyzed so that the sender is not confused with reciever becuase it is happending.
- format for the email:
Delivered-To: user1@example.com
MIME-Version: 1.0
From: "Zachary Quinn" <user2@example.net>
Date: Fri, 30 Jan 2015 15:53:46 +0000
Subject: Manage upon Congress history president under crime above.
To: "Cindy Dennis" <user1@example.com>
Cc: "Mrs. Kathleen Hart" <dillonmorgan@example.org>, "Jill Hess" <qhamilton@example.com>, "Brianna Singleton" <johnsonjerry@example.net>
Content-Type: multipart/alternative; boundary="00000000000091a0ba062bcdefca"

--00000000000091a0ba062bcdefca
Content-Type: text/plain; charset="UTF-8"
Content-Transfer-Encoding: quoted-printable

Any reality factor democratic speak husband would.
Marriage actually you although black ground know economy.
Huge society measure paper just picture under red. Great move product.

--00000000000091a0ba062bcdefca--

for this the answer is user2@example.net


#### 7. Extracting Credit Card Number
- the format of the image can be png or jpg and name can be credit-card or credit_card
- Use OCR tools (e.g., Tesseract) to extract the credit card number from an image.
- Write the number without spaces or special characters to the specified output file.
- The name of the PNG file can be `credit_card.png` or even `credit-card.png`.
- Use the Luhn algorithm to verify the 16-digit credit card number.
- The credit card number can be off by one digit (i.e., 1 out of 16 digits can be different, while the rest 15 digits should be the same), so some validation should be done before writing the output.
- Process and clean the extracted data as needed before writing it to the output.
- Use the following `luhn` function to validate the credit card number:

```python
def luhn(card_number):
    # Validate credit card number using the Luhn algorithm.
    def digits_of(n):
        return [int(d) for d in str(n)]
    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    return checksum % 10 == 0

#### 8. SQLite Query
- Query total sales for specific ticket types by multiplying `units` by `price`.
- Ensure that you include only relevant ticket types as per the query requirements.


#### 9. AI Endpoints You Can Leverage
You can use the following AI endpoints for specific tasks:
1. **Embeddings**:  
   - Endpoint: `POST https://aiproxy.sanand.workers.dev/openai/v1/embeddings`
   - Model: `text-embedding-3-small`
   - Use this endpoint for generating embeddings for text-based tasks.

2. **Chat Completions**:  
   - Endpoint: `POST https://aiproxy.sanand.workers.dev/openai/v1/chat/completions`
   - Model: `gpt-4o-mini`
   - Use this endpoint for conversational or generative AI tasks.

#### 10. For email related questions you should strictly follow the instructions like
- output should only be email id not the name unless mentioned that the name should also be included
- wrong email is being answer so some validation should be done before answering the email id
---

### General Notes:
1. Always validate input files for existence and proper format before processing.
2. Include comments in your Python code explaining each step for clarity.
3. Test edge cases such as empty files, malformed data, or missing fields.
4. Ensure that the output matches the expected format exactly to avoid errors.
5. Handle exceptions and errors gracefully to prevent script crashes.


Expected date formats:
30-Sep-2014
2000/03/20 05:44:16
2023-11-29
02-Aug-2019
24-May-2002
2009-01-23
2017/02/20 14:29:49
2010/11/20 04:44:55
2016-03-04
19-Feb-2009
Dec 14, 2001
28-Dec-2014
2006/03/19 07:10:43
2007-04-12
May 07, 2023
Oct 03, 2010
2021/11/10 07:40:47
Aug 09, 2002
2002-03-20
2020/06/25 11:20:25
24-Jul-2002
Jan 28, 2009
18-Dec-2005
2005-03-14
Jun 14, 2020
Sep 07, 2003
2004/05/22 00:28:16
2023-10-21
Aug 17, 2006
2014-09-28
2009-01-17
21-Jan-2009
2001/05/01 13:58:48
2005-10-02
2023/10/09 02:18:33
01-Oct-2021
Aug 10, 2023
2015/05/02 13:26:58
2001/12/18 07:25:01
18-Apr-2010
2012-09-26
2013/06/08 11:31:12
Nov 01, 2002
2011-07-14
2009-04-27
18-Aug-2015
Mar 27, 2010
23-Nov-2000
25-Dec-2000
Nov 22, 2013
Feb 12, 2002
Jun 11, 2010
Nov 05, 2017
03-Apr-2005
Oct 25, 2001
Jan 20, 2016
09-Apr-2001
Jul 08, 2018
2005/12/06 13:25:02
2022/01/31 15:14:37
07-Dec-2024
2005-01-08
2024-12-04
15-Nov-2010
2002-10-12
Mar 23, 2000
2007-07-04
2010-04-06
Oct 12, 2019
2021/01/11 03:31:56
25-Jul-2008
21-Aug-2003
2015/01/01 13:49:13
17-Jun-2016
2021/10/04 02:05:30
2008/12/14 21:28:41
13-Sep-2010
Nov 25, 2014
2001/11/18 23:36:04
Jul 29, 2005
Sep 21, 2012
02-May-2018
03-Mar-2007
08-Sep-2021
2021/04/14 20:55:21
14-Oct-2017
Jan 18, 2016
Sep 12, 2008
2002-07-23
24-Aug-2011
2012/04/03 04:43:56
2021-12-11
2000-07-21
2022/09/12 17:12:04
28-May-2018
2003/11/01 21:50:05
2018/11/22 16:00:34
20-Sep-2007
2000/04/29 11:06:30
2007/10/20 11:06:58
17-Jan-2009
2005-11-14
Jan 28, 2023
29-Mar-2003
2001/09/26 14:16:48
2002-01-24
2009-12-14
Aug 12, 2000
2023-10-11
2000-11-24
Aug 04, 2015
2016/02/20 20:40:18
11-Jul-2012
2009/06/28 18:13:45
2013-06-04
Aug 10, 2011
10-Dec-2006
2014/12/15 13:43:16
11-Dec-2014
2010/09/05 15:21:19
27-Apr-2010
Jun 06, 2022
18-Jan-2002
Jun 08, 2007
25-Jan-2012
2001/10/09 00:40:43
2006-02-17
19-Aug-2014
27-Jun-2008
2012/05/25 14:14:39
2002-11-19
08-Jun-2001
10-Feb-2019
2006-09-04
2016/02/14 03:56:17
10-May-2019
02-Apr-2011
2019/08/11 11:41:24
Sep 17, 2016
Jun 30, 2005
2009/04/10 04:17:32
2011-10-28
2002/12/07 12:13:08
2016-03-31
Oct 08, 2020
02-Nov-2003
30-Jan-2006
2024/02/20 14:19:31
07-Jan-2005
2009-01-03
Nov 09, 2011
2009-04-10
2003-06-07
Jul 24, 2004
Apr 14, 2020
2005-04-24
2009/02/28 17:15:58
2007-12-10
Sep 28, 2012
Sep 01, 2001
Aug 15, 2013
12-Jan-2018
2022-03-02
Apr 25, 2022
Jun 10, 2013
Nov 08, 2017
2016-04-09
17-Aug-2019
30-Oct-2021
24-May-2018
2007-05-06
08-Aug-2013
Jan 22, 2002
2020-03-19
2019-08-11
15-Oct-2008
22-Apr-2008
2006-07-25
27-Mar-2024
13-May-2016
Oct 16, 2005
May 05, 2015
2024/06/20 15:31:24
2022/06/23 17:34:08
15-Feb-2011
2020-09-02
2016/07/31 06:16:26
Mar 23, 2023
2024/10/11 15:32:51
2015-01-19
02-Jun-2001
2009/03/19 15:31:51
Jun 18, 2008
2009/08/20 08:43:16
2022-04-22
Jul 20, 2009
2024/10/28 13:50:42
2017/11/12 12:00:09
2013-07-18
2015/03/24 17:06:12
2001-05-02
Sep 19, 2016
22-Apr-2006
May 03, 2024
Dec 07, 2013
2014-01-29
28-Sep-2021
Mar 04, 2000
2014-11-04
2013/05/26 14:14:01
2013/01/16 07:36:31
11-Nov-2007
2004/07/06 13:28:00
Sep 07, 2017
2008-08-15
2013/09/25 02:25:02
14-Dec-2003
2007-03-14
21-Mar-2023
2009-09-02
May 22, 2020
2007-11-17
18-Jul-2002
Aug 31, 2007
2010/02/16 05:51:03
2000-03-02
2016-12-09
04-Jun-2020
2023/08/08 07:06:05
2006-04-13
11-May-2002
2007/01/10 12:25:06
2004-06-30
Nov 26, 2006
May 05, 2005
Aug 19, 2020
05-Jun-2018
2007/06/30 09:40:22
2017/09/01 20:04:02
Dec 17, 2002
2016/05/10 02:42:54
2016/02/11 00:08:46
Nov 04, 2022
Jul 04, 2020
2015/06/10 11:18:48
2002/09/15 07:21:22
2020-10-02
22-Jan-2006
2021-06-30
2021-12-24
2021-03-12
2005-09-02
2023-07-25
25-May-2020
16-May-2015
2009-08-08
08-Feb-2023
17-Oct-2011
Dec 14, 2008
2012/06/30 08:46:32
2013/01/09 22:54:39
2010/02/23 21:36:28
2005-08-15
2012-07-24
2011/02/11 22:35:45
2020/06/20 11:05:43
2008-09-11

"""

# Initialize CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (adjust for security)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variable for AI Proxy Token
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN")
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {AIPROXY_TOKEN}"
}


@app.get("/")
async def home():
    return {"message": "Welcome to Task Runner API"}


def validate_output_format(output: dict) -> bool:
    """Validate if the LLM's response is in the correct format."""
    required_keys = {"python_code", "python_dependencies"}
    if not isinstance(output, dict):
        return False
    if not required_keys.issubset(output.keys()):
        return False
    if not isinstance(output["python_code"], str):
        return False
    if not isinstance(output["python_dependencies"], list):
        return False
    return True


async def resend_request(task: str, code: str, error: str):
    """Resend request to LLM for updated code."""
    url = f"https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
    
    update_task_prompt = f"""
The previous response did not match the expected format or encountered an error during execution. 
Ensure that your response adheres strictly to this JSON schema:
{json.dumps(response_format['json_schema'], indent=2)}

Error encountered:
{error}

Update your response accordingly for this task:
{task}
"""
    
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": task},
            {"role": "system", "content": primary_prompt},
            {"role": "assistant", "content": code},
            {"role": "user", "content": update_task_prompt}
        ],
        "response_format": response_format
    }
    
    response = requests.post(url=url, headers=HEADERS, json=data)
    response.raise_for_status()
    
    return response.json()


async def llm_code_executor(python_dependencies, python_code):
    """Execute generated Python code."""
    # Prepare inline metadata script for dependencies
    inline_metadata_script = (
        "# /// script\n"
        "# requires-python = \">=3.11\"\n"
        "# dependencies = [\n"
        + ''.join(f"# \"{dependency['module']}\",\n" for dependency in python_dependencies)
        + "# ]\n"
        "# ///\n"
    )

    # Write the script to a file
    with open("llm_code.py", "w") as f:
        f.write(inline_metadata_script)
        f.write(python_code)

    try:
        # Run the script using uv
        output = run(
            ["uv", "run", "llm_code.py"],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        if output.returncode != 0:
            raise Exception(output.stderr)

        return {"status": "success", "output": output.stdout}
    
    except Exception as e:
        logging.error(f"Error executing code: {e}")
        return {"status": "error", "error_message": str(e)}


@app.post("/run")
async def task_runner(task: str):
    """Run a plain-English task."""
    url = f"https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

    # Request data for LLM
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": task},
            {"role": "system", "content": primary_prompt}
        ],
        "response_format": response_format
    }

    try:
        # Call LLM API to generate code and dependencies
        response = requests.post(url=url, headers=HEADERS, json=data)
        response.raise_for_status()
        
        r = response.json()
        
        content = json.loads(r['choices'][0]['message']['content'])
        
        if not validate_output_format(content):
            raise HTTPException(status_code=400, detail="Invalid response format from LLM.")
        
        python_dependencies = content['python_dependencies']
        python_code = content['python_code']

        # Execute generated code
        result = await llm_code_executor(python_dependencies, python_code)

        if result["status"] == "success":
            return {"message": result["output"]}
        
        # Retry logic in case of failure
        error_message = result["error_message"]
        
        retry_response = await resend_request(task, python_code, error_message)
        
        retry_content = json.loads(retry_response['choices'][0]['message']['content'])
        
        if not validate_output_format(retry_content):
            raise HTTPException(status_code=400, detail="Invalid retry response format from LLM.")
        
        python_dependencies_retry = retry_content['python_dependencies']
        python_code_retry = retry_content['python_code']
        
        final_result = await llm_code_executor(python_dependencies_retry, python_code_retry)
        
        if final_result["status"] == "success":
            return {"message": final_result["output"]}
        
        raise HTTPException(status_code=500, detail="Task execution failed after retries.")
    
    except Exception as e:
        logging.error(f"Task runner error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
from fastapi.responses import PlainTextResponse

@app.get("/read")
async def read_file(path: str):
    """Read file content."""
    try:
        if not path.startswith("/data/"):
            raise HTTPException(status_code=403, detail="Access to files outside /data is restricted.")

        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="File not found.")

        with open(path, 'r') as f:
            content = f.read()
        
        return PlainTextResponse(content=content)
    
    except Exception as e:
        logging.error(f"Error reading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

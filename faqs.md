Refer here for [Latest FAQs](https://github.com/modelteam-ai/modelteam.ai/blob/main/faqs.md)

**What languages does modelteam.ai support?**

Our model supports Python, Javascript, Java, Go, C, C++, PHP, Ruby, and C#. We are working on adding more languages to our model.

**Does modelteam.ai receive my code?**

No, modelteam.ai does not receive your code. The AI models run locally on your machine and do not send any data outside your machine. The generated profile contains only the metadata and predicted skills. The profile should also be manually uploaded to modelteam.ai. Please refer to our [Privacy Policy](https://modelteam.ai/#privacy) and [Terms of Service](https://modelteam.ai/#terms) for more information.

**How is the profile built?**

When you run the script with your local git repos, it scans the local git repos inside that input path using git commands. It does not connect to remote repositories or send any data outside your machine. Your code contributions are analyzed to generate a profile that includes your skills and quality score(beta).

**How long does it take to generate a profile?**

The time taken to generate a profile depends on the size of the codebase. We recommend disabling sleep mode and running the script at night or when you are not using the computer. This will ensure that the script runs without interruptions.
This is a one-time effort and the generated profile can be reused for multiple job applications.

**How do I get started with modelteam.ai?**

Sign up on modelteam.ai and follow the instructions to generate your profile.

**What LLMs does modelteam.ai use?**

We have our own LLMs that are fine-tuned versions of [Salesforce/CodeT5p 770M](https://huggingface.co/Salesforce/CodeT5P-770M). They are used to predict the skills and quality score(beta) from the code snippets.

**Need more help?**

Please reach out to support@modelteam.ai for any queries or issues.
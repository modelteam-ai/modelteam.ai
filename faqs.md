# [Latest FAQs](https://github.com/modelteam-ai/modelteam.ai/blob/main/faqs.md)

## **What languages does modelteam.ai support?**
Modelteam.ai currently supports the following programming languages:  
Python, JavaScript, TypeScript, Java, Go, C, C++, PHP, Ruby, C#, Rust, Scala, Swift, Kotlin, Lua, Dart, and Elixir.  

We’re continuously working to add support for more languages. Stay tuned for updates!

---

## **Does modelteam.ai receive my code?**
**No**, modelteam.ai does not receive or store your code. We bring our code and AI models to your local machine, ensuring your code remains private. 

- The AI models run locally on your machine, ensuring no data is sent outside your environment.  
- The generated profile includes only metadata and predicted skills.  
- Profiles must be manually uploaded to modelteam.ai.  

For more information, please review our [Privacy Policy](https://modelteam.ai/#privacy) and [Terms of Service](https://modelteam.ai/#terms).

---

## **How is the profile built?**
The profile is generated using your local git repositories:  
- The script scans repositories located in the specified input path using `git` commands.  
- It does **not** connect to remote repositories or send data externally.  
- The analysis focuses **only on your code contributions** to generate a profile containing your skills and quality score (beta).  

---

## **How long does it take to generate a profile?**
The time required depends on the size of your codebase.  

- For larger repositories, it’s recommended to disable sleep mode and run the script overnight or when your computer is idle.  
- This is a **one-time effort**, and the generated profile can be reused.  

---

## **How do I get started with modelteam.ai?**
1. Sign up on [modelteam.ai](https://modelteam.ai).  
2. Follow the provided instructions to generate and upload your profile.  

---

## **What LLMs does modelteam.ai use?**
Modelteam.ai uses fine-tuned versions of [Salesforce/CodeT5p 770M](https://huggingface.co/Salesforce/CodeT5P-770M).  

These models analyze code snippets to predict skills and calculate a quality score (beta).

---

## **What are the badges in the profile?**
Profiles feature **badges** to highlight your strengths:  
- **Programming Languages**: Quantity and Quality badges indicate your expertise.  
- **Skills**: Quantity badges showcase your proficiency.  

Your scores are compared against tens of thousands of developers to determine if you rank in the top percentile for a specific language or skill.

---

## **Need more help?**
If you have any questions or encounter issues, please contact us at [support@modelteam.ai](mailto:support@modelteam.ai).  

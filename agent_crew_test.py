from saarthi_assistant.crew.main import CustomCrew

if __name__ == "__main__":
    custom_crew = CustomCrew()
    
    # Choose which example to run
    # result = custom_crew.run()  # Original research example
    # result = custom_crew.run_identity_example()  # Identity management example
    result = custom_crew.run_enrollment_example()  # User enrollment example
    
    # result = custom_crew.run()
    print("\n\n########################")
    print("## Here is you custom crew run result:")
    print("########################\n")
    print(result)
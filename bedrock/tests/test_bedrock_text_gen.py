from bedrock_text_gen import call_bedrock

# make test method:
def test_call_bedrock():
    response = call_bedrock("What is the earth's natural satellite called?")

    # assert that the response contains the word "moon":
    print(response)
    assert isinstance(response, str)
    assert "moon" in response


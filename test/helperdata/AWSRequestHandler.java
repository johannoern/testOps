package org.example;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;

public class AWSRequestHandler implements RequestHandler<Object, String> {
    @Override
    public String handleRequest(Object input, Context context) {
        String output="";
        output = HelloWorld.main(input);
        return output;
    }
}
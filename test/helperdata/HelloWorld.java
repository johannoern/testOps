package org.example;

import org.joda.time.LocalTime;

public class HelloWorld {
    public static String main(String input) {
        LocalTime currentTime = new LocalTime();
        System.out.println("The current local time is: " + currentTime);

        System.out.println("I am soo happy");

        Greeter greeter = new Greeter();
        System.out.println(greeter.sayHello());
    }
}
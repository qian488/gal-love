package com.example.gallove;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;

@SpringBootApplication
@EnableJpaAuditing
public class GalLoveApplication {
    public static void main(String[] args) {
        SpringApplication.run(GalLoveApplication.class, args);
    }
}

package com.example.gallove.controller;

import com.example.gallove.common.Result;
import com.example.gallove.dto.LoginRequest;
import com.example.gallove.dto.RegisterRequest;
import com.example.gallove.service.AuthService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/register")
    public Result<?> register(@RequestBody RegisterRequest request) {
        try {
            authService.register(request);
            return Result.success("Registration successful");
        } catch (RuntimeException e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/login")
    public Result<?> login(@RequestBody LoginRequest request) {
        try {
            var result = authService.login(request);
            return Result.success(result);
        } catch (Exception e) {
            return Result.error("Invalid username or password");
        }
    }
}

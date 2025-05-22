package com.example.gallove.controller;

import com.example.gallove.common.Result;
import com.example.gallove.dto.UpdateProfileRequest;
import com.example.gallove.model.User;
import com.example.gallove.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/user")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    @GetMapping("/profile")
    public Result<User> getProfile() {
        try {
            User user = userService.getCurrentUser();
            return Result.success(user);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PutMapping("/profile")
    public Result<User> updateProfile(@RequestBody UpdateProfileRequest request) {
        try {
            User updatedUser = userService.updateProfile(request);
            return Result.success(updatedUser);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
}

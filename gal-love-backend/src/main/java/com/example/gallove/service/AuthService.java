package com.example.gallove.service;

import com.example.gallove.dto.LoginRequest;
import com.example.gallove.dto.RegisterRequest;
import com.example.gallove.model.User;
import com.example.gallove.repository.UserRepository;
import com.example.gallove.util.JwtUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;
    private final AuthenticationManager authenticationManager;

    public Map<String, Object> login(LoginRequest request) {
        // 首先尝试验证用户名和密码
        try {
            authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(request.getUsername(), request.getPassword())
            );
        } catch (Exception e) {
            throw new RuntimeException("Invalid username or password");
        }

        // 获取用户信息并生成 token
        var user = userRepository.findByUsername(request.getUsername())
            .orElseThrow(() -> new RuntimeException("User not found"));
        
        var token = jwtUtil.generateToken(user);
        
        // 构建去除密码的用户信息
        var userMap = new HashMap<String, Object>();
        userMap.put("id", user.getId());
        userMap.put("username", user.getUsername());
        userMap.put("email", user.getEmail());
        userMap.put("avatar", user.getAvatar());
        userMap.put("createTime", user.getCreateTime());
        
        Map<String, Object> result = new HashMap<>();
        result.put("token", token);
        result.put("user", userMap);
        return result;
    }

    public void register(RegisterRequest request) {
        // 验证用户名和邮箱是否已存在
        if (userRepository.existsByUsername(request.getUsername())) {
            throw new RuntimeException("Username already exists");
        }
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new RuntimeException("Email already exists");
        }

        // 创建新用户
        User user = new User();
        user.setUsername(request.getUsername());
        user.setEmail(request.getEmail());
        user.setPassword(passwordEncoder.encode(request.getPassword()));

        userRepository.save(user);
    }
}

package com.example.gallove.dto;

import lombok.Data;

@Data
public class UpdateProfileRequest {
    private String email;
    private String avatar;
    // 可以根据需求添加其他字段
}

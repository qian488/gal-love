package com.example.gallove.dto;

import lombok.Data;

@Data
public class GameQueryRequest {
    private Integer page = 1;
    private Integer limit = 10;
    private String search;
    private String tag;
}

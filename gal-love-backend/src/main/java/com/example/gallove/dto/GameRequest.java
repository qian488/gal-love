package com.example.gallove.dto;

import lombok.Data;
import java.util.Set;

@Data
public class GameRequest {
    private String title;
    private String description;
    private String coverImage;
    private Set<String> tags;
}

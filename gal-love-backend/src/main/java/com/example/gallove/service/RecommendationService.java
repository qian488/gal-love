package com.example.gallove.service;

import com.example.gallove.model.Game;
import com.example.gallove.model.GameRating;
import com.example.gallove.model.User;
import com.example.gallove.repository.GameRatingRepository;
import com.example.gallove.repository.GameRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class RecommendationService {
    
    private final GameRepository gameRepository;
    private final GameRatingRepository ratingRepository;
    private final UserService userService;
    
    public List<Game> getRecommendedGames(int limit) {
        User currentUser = userService.getCurrentUser();
        
        // 1. 获取用户最近评分过的游戏的标签
        Set<String> userPreferredTags = getUserPreferredTags(currentUser);
        
        // 2. 获取评分最高的游戏
        List<Game> topRatedGames = gameRepository.findAll(
            PageRequest.of(0, limit, Sort.by(Sort.Direction.DESC, "averageRating"))
        ).getContent();
        
        // 3. 基于用户偏好标签的游戏
        List<Game> recommendedGames = new ArrayList<>();
        if (!userPreferredTags.isEmpty()) {
            recommendedGames = gameRepository.findAll().stream()
                .filter(game -> !game.getTags().isEmpty() && 
                    game.getTags().stream().anyMatch(userPreferredTags::contains))
                .sorted((g1, g2) -> Double.compare(g2.getAverageRating(), g1.getAverageRating()))
                .limit(limit)
                .collect(Collectors.toList());
        }
        
        // 4. 合并结果并去重
        Set<Long> addedGameIds = new HashSet<>();
        List<Game> finalRecommendations = new ArrayList<>();
        
        // 首先添加基于标签的推荐
        for (Game game : recommendedGames) {
            if (addedGameIds.add(game.getId())) {
                finalRecommendations.add(game);
            }
        }
        
        // 然后添加评分最高的游戏
        for (Game game : topRatedGames) {
            if (finalRecommendations.size() >= limit) break;
            if (addedGameIds.add(game.getId())) {
                finalRecommendations.add(game);
            }
        }
        
        return finalRecommendations;
    }
    
    private Set<String> getUserPreferredTags(User user) {
        return gameRepository.findAll().stream()
            .filter(game -> hasUserRated(user.getId(), game.getId()))
            .flatMap(game -> game.getTags().stream())
            .collect(Collectors.toSet());
    }
    
    private boolean hasUserRated(Long userId, Long gameId) {
        return ratingRepository.findByUserIdAndGameId(userId, gameId).isPresent();
    }
}

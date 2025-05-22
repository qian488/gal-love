package com.example.gallove.controller;

import com.example.gallove.common.Result;
import com.example.gallove.dto.CommentRequest;
import com.example.gallove.dto.GameQueryRequest;
import com.example.gallove.dto.GameRequest;
import com.example.gallove.dto.RatingRequest;
import com.example.gallove.model.Game;
import com.example.gallove.model.GameComment;
import com.example.gallove.model.GameRating;
import com.example.gallove.service.GameService;
import com.example.gallove.service.RecommendationService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Set;

@RestController
@RequestMapping("/games")
@RequiredArgsConstructor
public class GameController {

    private final GameService gameService;
    private final RecommendationService recommendationService;

    @GetMapping
    public Result<Page<Game>> getGames(GameQueryRequest request) {
        try {
            Page<Game> games = gameService.getGames(request);
            return Result.success(games);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/{id}")
    public Result<Game> getGame(@PathVariable Long id) {
        try {
            Game game = gameService.getGameById(id);
            return Result.success(game);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Game> createGame(@RequestBody GameRequest request) {
        try {
            Game game = gameService.createGame(request);
            return Result.success(game);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PutMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Game> updateGame(@PathVariable Long id, @RequestBody GameRequest request) {
        try {
            Game game = gameService.updateGame(id, request);
            return Result.success(game);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<Void> deleteGame(@PathVariable Long id) {
        try {
            gameService.deleteGame(id);
            return Result.success();
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/tags")
    public Result<Set<String>> getAllTags() {
        try {
            Set<String> tags = gameService.getAllTags();
            return Result.success(tags);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/{id}/rate")
    public Result<?> rateGame(@PathVariable Long id, @RequestBody RatingRequest request) {
        try {
            GameRating rating = gameService.rateGame(id, request);
            return Result.success(rating);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/{id}/rating")
    public Result<?> getUserRating(@PathVariable Long id) {
        try {
            Integer rating = gameService.getUserRating(id);
            return Result.success(rating);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/{id}/comments")
    public Result<?> addComment(@PathVariable Long id, @RequestBody CommentRequest request) {
        try {
            GameComment comment = gameService.addComment(id, request);
            return Result.success(comment);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/{id}/comments")
    public Result<?> getComments(
            @PathVariable Long id,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        try {
            Page<GameComment> comments = gameService.getComments(id, page, size);
            return Result.success(comments);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/recommendations")
    public Result<?> getRecommendations(@RequestParam(defaultValue = "10") int limit) {
        try {
            List<Game> recommendations = recommendationService.getRecommendedGames(limit);
            return Result.success(recommendations);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
}

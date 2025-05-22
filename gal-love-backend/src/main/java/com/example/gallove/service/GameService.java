package com.example.gallove.service;

import com.example.gallove.dto.GameQueryRequest;
import com.example.gallove.dto.GameRequest;
import com.example.gallove.dto.RatingRequest;
import com.example.gallove.dto.CommentRequest;
import com.example.gallove.model.Game;
import com.example.gallove.model.GameRating;
import com.example.gallove.model.GameComment;
import com.example.gallove.model.User;
import com.example.gallove.repository.GameRatingRepository;
import com.example.gallove.repository.GameRepository;
import com.example.gallove.repository.GameCommentRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Set;

@Service
@RequiredArgsConstructor
public class GameService {

    private final GameRepository gameRepository;
    private final GameRatingRepository gameRatingRepository;
    private final GameCommentRepository commentRepository;
    private final UserService userService;

    public Page<Game> getGames(GameQueryRequest request) {
        PageRequest pageRequest = PageRequest.of(
            request.getPage() - 1,
            request.getLimit(),
            Sort.by(Sort.Direction.DESC, "createTime")
        );

        return gameRepository.findByFilters(
            request.getSearch(),
            request.getTag(),
            pageRequest
        );
    }

    public Game getGameById(Long id) {
        return gameRepository.findById(id)
            .orElseThrow(() -> new RuntimeException("Game not found"));
    }

    @Transactional
    public Game createGame(GameRequest request) {
        Game game = new Game();
        game.setTitle(request.getTitle());
        game.setDescription(request.getDescription());
        game.setCoverImage(request.getCoverImage());
        game.setTags(request.getTags());
        game.setAverageRating(0.0);
        game.setRatingCount(0);
        
        return gameRepository.save(game);
    }

    @Transactional
    public Game updateGame(Long id, GameRequest request) {
        Game game = getGameById(id);
        
        game.setTitle(request.getTitle());
        game.setDescription(request.getDescription());
        game.setCoverImage(request.getCoverImage());
        game.setTags(request.getTags());
        
        return gameRepository.save(game);
    }

    public void deleteGame(Long id) {
        gameRepository.deleteById(id);
    }

    public Set<String> getAllTags() {
        return gameRepository.findAllTags();
    }

    @Transactional
    public GameRating rateGame(Long gameId, RatingRequest request) {
        Game game = getGameById(gameId);
        User user = userService.getCurrentUser();
        
        // 检查用户是否已经评分过
        GameRating rating = gameRatingRepository
            .findByUserIdAndGameId(user.getId(), gameId)
            .orElse(new GameRating());
        
        rating.setUser(user);
        rating.setGame(game);
        rating.setRating(request.getRating());
        
        GameRating savedRating = gameRatingRepository.save(rating);
        
        // 更新游戏的平均评分
        updateGameRating(game);
        
        return savedRating;
    }

    private void updateGameRating(Game game) {
        Double avgRating = gameRatingRepository.getAverageRatingByGameId(game.getId());
        Integer ratingCount = gameRatingRepository.getRatingCountByGameId(game.getId());
        
        game.setAverageRating(avgRating != null ? avgRating : 0.0);
        game.setRatingCount(ratingCount != null ? ratingCount : 0);
        
        gameRepository.save(game);
    }

    public Integer getUserRating(Long gameId) {
        User user = userService.getCurrentUser();
        return gameRatingRepository
            .findByUserIdAndGameId(user.getId(), gameId)
            .map(GameRating::getRating)
            .orElse(null);
    }

    @Transactional
    public GameComment addComment(Long gameId, CommentRequest request) {
        Game game = getGameById(gameId);
        User user = userService.getCurrentUser();
        
        GameComment comment = new GameComment();
        comment.setGame(game);
        comment.setUser(user);
        comment.setContent(request.getContent());
        
        return commentRepository.save(comment);
    }

    public Page<GameComment> getComments(Long gameId, int page, int size) {
        return commentRepository.findByGameId(
            gameId,
            PageRequest.of(page - 1, size, Sort.by(Sort.Direction.DESC, "createTime"))
        );
    }
}

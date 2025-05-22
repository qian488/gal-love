package com.example.gallove.repository;

import com.example.gallove.model.GameRating;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.Optional;

public interface GameRatingRepository extends JpaRepository<GameRating, Long> {
    Optional<GameRating> findByUserIdAndGameId(Long userId, Long gameId);
    
    @Query("SELECT AVG(r.rating) FROM GameRating r WHERE r.game.id = :gameId")
    Double getAverageRatingByGameId(Long gameId);
    
    @Query("SELECT COUNT(r) FROM GameRating r WHERE r.game.id = :gameId")
    Integer getRatingCountByGameId(Long gameId);
}

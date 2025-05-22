package com.example.gallove.repository;

import com.example.gallove.model.GameComment;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface GameCommentRepository extends JpaRepository<GameComment, Long> {
    Page<GameComment> findByGameId(Long gameId, Pageable pageable);
}

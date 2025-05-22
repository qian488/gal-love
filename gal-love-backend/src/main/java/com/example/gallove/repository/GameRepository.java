package com.example.gallove.repository;

import com.example.gallove.model.Game;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import java.util.Set;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface GameRepository extends JpaRepository<Game, Long> {
    
    @Query("SELECT g FROM Game g WHERE " +
           "(:search IS NULL OR LOWER(g.title) LIKE LOWER(CONCAT('%', :search, '%'))) AND " +
           "(:tag IS NULL OR :tag MEMBER OF g.tags)")
    Page<Game> findByFilters(@Param("search") String search,
                            @Param("tag") String tag,
                            Pageable pageable);

    @Query("SELECT DISTINCT t FROM Game g JOIN g.tags t")
    Set<String> findAllTags();
}

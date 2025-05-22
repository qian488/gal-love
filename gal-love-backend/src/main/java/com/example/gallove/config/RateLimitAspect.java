package com.example.gallove.config;

import com.example.gallove.common.Result;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.util.concurrent.TimeUnit;

@Aspect
@Component
@RequiredArgsConstructor
public class RateLimitAspect {

    private final RedisTemplate<String, Object> redisTemplate;

    @Around("@annotation(rateLimit)")
    public Object around(ProceedingJoinPoint joinPoint, RateLimit rateLimit) throws Throwable {
        HttpServletRequest request = ((ServletRequestAttributes) RequestContextHolder.getRequestAttributes()).getRequest();
        String ip = request.getRemoteAddr();
        String key = "rate_limit:" + ip + ":" + joinPoint.getSignature().getName();
        
        // 获取当前访问次数
        Integer count = (Integer) redisTemplate.opsForValue().get(key);
        if (count == null) {
            // 第一次访问
            redisTemplate.opsForValue().set(key, 1, 1, TimeUnit.MINUTES);
        } else if (count < rateLimit.value()) {
            // 未超过限制
            redisTemplate.opsForValue().increment(key);
        } else {
            // 超过限制
            return Result.error(429, "请求过于频繁，请稍后再试");
        }
        
        return joinPoint.proceed();
    }
}

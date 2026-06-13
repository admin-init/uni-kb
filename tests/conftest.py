from __future__ import annotations

import pytest
from uni_kb.parsers.base import ParseResult

SAMPLE_CONTROLLER = """\
package com.example.controller;

import org.springframework.web.bind.annotation.*;
import org.springframework.security.access.prepost.PreAuthorize;

@RestController
@RequestMapping("/api/users")
public class UserController {

    @GetMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public User getUser(@PathVariable Long id) {
        return null;
    }

    @PostMapping(consumes = "application/json", produces = "application/json")
    public User createUser(@RequestBody User user) {
        return null;
    }

    @DeleteMapping("/{id}")
    public void deleteUser(@PathVariable Long id) {
    }

    @PutMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN') or hasRole('MANAGER')")
    public User updateUser(@PathVariable Long id, @RequestBody User user) {
        return null;
    }
}
"""

SAMPLE_SERVICE = """\
package com.example.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;
import com.example.repository.UserRepository;

@Service
public class UserService {

    @Autowired
    private UserRepository userRepository;

    public User findById(Long id) {
        return userRepository.findById(id).orElse(null);
    }

    @Transactional
    public User create(User user) {
        return userRepository.save(user);
    }

    public void delete(Long id) {
        userRepository.deleteById(id);
    }
}
"""

SAMPLE_ENTITY = """\
package com.example.entity;

import javax.persistence.*;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Size;

@Entity
@Table(name = "users", indexes = {
    @Index(name = "idx_email", columnList = "email", unique = true)
})
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "username", nullable = false, unique = true, length = 50)
    @NotNull
    @Size(max = 50)
    private String username;

    @Column(name = "email", nullable = false, unique = true)
    private String email;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "department_id")
    private Department department;

    @Transient
    private String tempField;
}
"""

SAMPLE_MAPPER_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
    "http://mybatis.org/dtd/mapper">
<mapper namespace="com.example.mapper.UserMapper">

    <select id="findById" resultType="com.example.entity.User" parameterType="Long">
        SELECT * FROM users WHERE id = #{id}
    </select>

    <insert id="insert" parameterType="com.example.entity.User">
        INSERT INTO users (username, email) VALUES (#{username}, #{email})
    </insert>

    <update id="update" parameterType="com.example.entity.User">
        UPDATE users SET username = #{username}, email = #{email} WHERE id = #{id}
    </update>

    <delete id="deleteById" parameterType="Long">
        DELETE FROM users WHERE id = #{id}
    </delete>

</mapper>
"""

SAMPLE_MAPPER_JAVA = """\
package com.example.mapper;

import org.apache.ibatis.annotations.*;
import com.example.entity.User;

@Mapper
public interface UserMapper {

    @Select("SELECT * FROM users WHERE id = #{id}")
    User findById(Long id);

    @Insert("INSERT INTO users (username, email) VALUES (#{username}, #{email})")
    void insert(User user);

    @Update("UPDATE users SET username = #{username}, email = #{email} WHERE id = #{id}")
    void update(User user);

    @Delete("DELETE FROM users WHERE id = #{id}")
    void deleteById(Long id);
}
"""


@pytest.fixture
def controller_source() -> str:
    return SAMPLE_CONTROLLER


@pytest.fixture
def service_source() -> str:
    return SAMPLE_SERVICE


@pytest.fixture
def entity_source() -> str:
    return SAMPLE_ENTITY


@pytest.fixture
def mapper_xml_source() -> str:
    return SAMPLE_MAPPER_XML


@pytest.fixture
def mapper_java_source() -> str:
    return SAMPLE_MAPPER_JAVA


@pytest.fixture
def empty_result() -> ParseResult:
    return ParseResult()

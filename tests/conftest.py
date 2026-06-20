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


SAMPLE_EXPRESS_ROUTES = """\
const express = require('express');
const router = express.Router();
const auth = require('../middleware/auth');

router.use('/api/users');

router.get('/:id', auth, (req, res) => {
    res.json({ id: req.params.id });
});

router.post('/', auth.hasRole('ADMIN'), (req, res) => {
    res.status(201).json(req.body);
});

router.put('/:id', verifyToken, (req, res) => {
    res.json({ updated: true });
});

router.delete('/:id', (req, res) => {
    res.status(204).send();
});

module.exports = router;
"""

SAMPLE_NESTJS_CONTROLLER = """\
import { Controller, Get, Post, Put, Delete, Param, Body } from '@nestjs/common';

@Controller('users')
export class UserController {

    @Get(':id')
    async getUser(@Param('id') id: string) {
        return { id };
    }

    @Post()
    async createUser(@Body() body: any) {
        return body;
    }

    @Put(':id')
    async updateUser(@Param('id') id: string, @Body() body: any) {
        return { id, ...body };
    }

    @Delete(':id')
    async deleteUser(@Param('id') id: string) {
        return { deleted: true };
    }
}
"""

SAMPLE_NESTJS_SERVICE = """\
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User } from './user.entity';

@Injectable()
export class UserService {

    constructor(
        @InjectRepository(User)
        private userRepository: Repository<User>,
    ) {}

    async findById(id: number): Promise<User> {
        return this.userRepository.findOne({ where: { id } });
    }

    async create(data: Partial<User>): Promise<User> {
        return this.userRepository.save(data);
    }

    async delete(id: number): Promise<void> {
        await this.userRepository.delete(id);
    }
}
"""

SAMPLE_SEQUELIZE_MODEL = """\
const { DataTypes } = require('sequelize');
const sequelize = require('../config/database');

const User = sequelize.define('users', {
    id: {
        type: DataTypes.INTEGER,
        primaryKey: true,
        autoIncrement: true,
    },
    username: {
        type: DataTypes.STRING,
        allowNull: false,
        unique: true,
    },
    email: {
        type: DataTypes.STRING,
        allowNull: false,
        unique: true,
        field: 'email_address',
    },
    departmentId: {
        type: DataTypes.INTEGER,
        allowNull: true,
        references: {
            model: 'departments',
            key: 'id',
        },
    },
});

module.exports = User;
"""

SAMPLE_TYPEORM_ENTITY = """\
import { Entity, PrimaryGeneratedColumn, Column, ManyToOne, JoinColumn } from 'typeorm';

@Entity({ name: 'users' })
export class User {

    @PrimaryGeneratedColumn()
    id: number;

    @Column({ name: 'username', nullable: false, unique: true })
    username: string;

    @Column({ nullable: false, unique: true })
    email: string;

    @ManyToOne(() => Department)
    @JoinColumn({ name: 'department_id' })
    department: Department;
}
"""

SAMPLE_MIDDLEWARE = """\
const jwt = require('jsonwebtoken');

function verifyToken(req, res, next) {
    const token = req.headers['authorization'];
    if (!token) return res.status(401).send('Unauthorized');
    jwt.verify(token, process.env.SECRET, (err, decoded) => {
        if (err) return res.status(403).send('Forbidden');
        req.user = decoded;
        next();
    });
}

function hasRole(requiredRole) {
    return (req, res, next) => {
        if (!req.user || req.user.role !== requiredRole) {
            return res.status(403).send('Forbidden');
        }
        next();
    };
}

module.exports = { verifyToken, hasRole };
"""


@pytest.fixture
def empty_result() -> ParseResult:
    return ParseResult()


@pytest.fixture
def express_source() -> str:
    return SAMPLE_EXPRESS_ROUTES


@pytest.fixture
def nestjs_source() -> str:
    return SAMPLE_NESTJS_CONTROLLER


@pytest.fixture
def nestjs_service_source() -> str:
    return SAMPLE_NESTJS_SERVICE


@pytest.fixture
def sequelize_source() -> str:
    return SAMPLE_SEQUELIZE_MODEL


@pytest.fixture
def typeorm_source() -> str:
    return SAMPLE_TYPEORM_ENTITY


@pytest.fixture
def middleware_source() -> str:
    return SAMPLE_MIDDLEWARE


@pytest.fixture
def petclinic_path():
    """Path to spring-petclinic-rest test fixture project."""
    from pathlib import Path
    p = (
        Path(__file__).resolve().parent.parent.parent
        / "tests" / "spring-petclinic-rest"
    )
    if not p.exists():
        pytest.skip("spring-petclinic-rest fixture not found")
    return str(p)

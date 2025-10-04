package main

import (
	"context"
	"log"
	"os"
	"strings"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"go.uber.org/zap"

	"github.com/genovotechnologies/synthos_dev/backend-go/internal/auth"
	"github.com/genovotechnologies/synthos_dev/backend-go/internal/cache"
	"github.com/genovotechnologies/synthos_dev/backend-go/internal/config"
	"github.com/genovotechnologies/synthos_dev/backend-go/internal/db"
	v1 "github.com/genovotechnologies/synthos_dev/backend-go/internal/http/v1"
	"github.com/genovotechnologies/synthos_dev/backend-go/internal/logger"
	"github.com/genovotechnologies/synthos_dev/backend-go/internal/middleware"
	"github.com/genovotechnologies/synthos_dev/backend-go/internal/repo"
	"github.com/genovotechnologies/synthos_dev/backend-go/internal/services"
	"github.com/genovotechnologies/synthos_dev/backend-go/internal/usage"
)

func main() {
	cfg := config.Load()
	logg, _ := logger.New(cfg.Environment)
	defer logg.Sync()
	sugar := logg.Sugar()

	// Init DB
	database, err := db.New(cfg.DatabaseURL)
	if err != nil {
		logg.Fatal("db init failed", zap.Error(err))
	}
	defer database.SQL.Close()

	// Init Redis
	redisClient, err := cache.New(cfg.RedisURL)
	if err != nil {
		logg.Fatal("redis init failed", zap.Error(err))
	}

	app := fiber.New(fiber.Config{AppName: "Synthos API (Go)"})

	// Basic CORS for now; will harden with config later
	app.Use(cors.New(cors.Config{
		AllowOrigins:     strings.Join(cfg.CorsOrigins, ","),
		AllowCredentials: true,
		AllowHeaders:     "*",
		AllowMethods:     "GET,POST,PUT,DELETE,PATCH,OPTIONS",
	}))

	// Register security & platform middlewares
	_ = middleware.Register(app, middleware.Options{
		AllowedHosts: cfg.CorsOrigins, // reuse for now or add separate env
		ForceHTTPS:   cfg.Environment == "production",
		RateLimitRPS: 100,
		SessionKey:   cfg.JwtSecret,
		RedisURL:     cfg.RedisURL,
	})

	// Health endpoints
	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "healthy"})
	})
	app.Get("/health/ready", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "ready"})
	})
	app.Get("/health/live", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "alive"})
	})

	// v1 router scaffold aligned with frontend expectations
	// Create repositories and deps
	userRepo := repo.NewUserRepo(database.SQL)
	if err := userRepo.CreateSchema(context.Background()); err != nil {
		logg.Fatal("failed to create user schema", zap.Error(err))
	}

	datasetRepo := repo.NewDatasetRepo(database.SQL)
	if err := datasetRepo.CreateSchema(context.Background()); err != nil {
		logg.Fatal("failed to create dataset schema", zap.Error(err))
	}

	genRepo := repo.NewGenerationRepo(database.SQL)
	if err := genRepo.CreateSchema(context.Background()); err != nil {
		logg.Fatal("failed to create generation schema", zap.Error(err))
	}

	// Initialize custom model repo
	customModelRepo := repo.NewCustomModelRepo(database.SQL)
	if err := customModelRepo.CreateSchema(context.Background()); err != nil {
		logg.Fatal("failed to create custom model schema", zap.Error(err))
	}

	bl := auth.NewBlacklist(redisClient.Client)

	usageService := usage.NewUsageService(userRepo, genRepo, datasetRepo, customModelRepo)

	// Initialize advanced repositories
	userUsageRepo := repo.NewUserUsageRepo(database.SQL)
	if err := userUsageRepo.CreateSchema(context.Background()); err != nil {
		logg.Fatal("failed to create user usage schema", zap.Error(err))
	}

	userSubRepo := repo.NewUserSubscriptionRepo(database.SQL)
	if err := userSubRepo.CreateSchema(context.Background()); err != nil {
		logg.Fatal("failed to create user subscription schema", zap.Error(err))
	}

	apiKeyRepo := repo.NewAPIKeyRepo(database.SQL)
	if err := apiKeyRepo.CreateSchema(context.Background()); err != nil {
		logg.Fatal("failed to create API key schema", zap.Error(err))
	}

	auditLogRepo := repo.NewAuditLogRepo(database.SQL)
	if err := auditLogRepo.CreateSchema(context.Background()); err != nil {
		logg.Fatal("failed to create audit log schema", zap.Error(err))
	}

	// Initialize advanced auth service
	advancedAuthService := auth.NewAdvancedAuthService(redisClient.Client, bl)

	// Initialize email service
	emailService := services.NewEmailService(
		cfg.SMTPHost, cfg.SMTPPort, cfg.SMTPUsername, cfg.SMTPPassword,
		cfg.FromEmail, cfg.FromName,
	)

	// Initialize Vertex AI handlers
	vertexAIHandlers, err := v1.NewVertexAIHandlers(cfg)
	if err != nil {
		logg.Fatal("failed to initialize Vertex AI handlers", zap.Error(err))
	}

	// Initialize storage client based on provider
	var storageClient v1.SignedURLProvider
	if cfg.StorageProvider == "gcs" && cfg.GCSBucket != "" {
		// GCS storage initialization would go here
		// storageClient, _ = storage.NewGCSProvider(context.Background(), cfg.GCSBucket)
	} else if cfg.StorageProvider == "s3" {
		// S3 storage initialization would go here
		// storageClient, _ = storage.NewS3Provider(context.Background(), cfg.S3Bucket, cfg.S3Region)
	}

	v1.Register(app, v1.Deps{
		Auth: v1.AuthDeps{
			Users:        userRepo,
			APIKeys:      apiKeyRepo,
			AuditLogs:    auditLogRepo,
			AuthService:  advancedAuthService,
			EmailService: emailService,
			Blacklist:    bl,
		},
		Users: v1.UserDeps{Users: userRepo},
		Datasets: v1.DatasetDeps{
			Datasets:      datasetRepo,
			Usage:         usageService,
			StorageClient: storageClient,
		},
		Generations: v1.GenerationDeps{
			Generations:   genRepo,
			Usage:         usageService,
			StorageClient: storageClient,
		},
		Payments: v1.PaymentDeps{
			StripeWebhookSecret: cfg.StripeSecretKey,
			PaddlePublicKey:     cfg.PaddlePublicKey,
		},
		Analytics:    v1.AnalyticsDeps{},
		Privacy:      v1.PrivacyDeps{},
		Admin:        v1.AdminDeps{Users: userRepo},
		Usage:        v1.UsageDeps{Usage: usageService},
		CustomModels: v1.CustomModelDeps{CustomModels: customModelRepo},
		VertexAI:     vertexAIHandlers,
	})

	_ = redisClient // will be used in auth/token blacklist etc.

	// Use PORT environment variable for Cloud Run, fallback to config
	port := os.Getenv("PORT")
	if port == "" {
		port = cfg.Port
	}

	addr := ":" + port
	sugar.Infof("Starting Synthos Go API on %s", addr)
	if err := app.Listen(addr); err != nil {
		log.Fatal(err)
	}
}

// keep file local helpers minimal

package main

import (
	"bytes"
	"context"
	"encoding/json"
	"log"
	"net/http"
	"time"
)

// SlackNotifier posts messages to Slack via chat.postMessage. It is a no-op
// when the bot token is empty, and it swallows all send errors (logging only),
// mirroring scripts/sendslackmsg.sh's robustness policy.
type SlackNotifier struct {
	Token   string
	Channel string
	Client  *http.Client
}

// NewSlackNotifier builds a notifier from config.
func NewSlackNotifier(cfg Config) *SlackNotifier {
	return &SlackNotifier{
		Token:   cfg.SlackBotToken,
		Channel: cfg.SlackChannel,
		Client:  &http.Client{Timeout: 10 * time.Second},
	}
}

// Notify sends text to the configured channel. No-op when token is unset.
func (s *SlackNotifier) Notify(text string) {
	if s.Token == "" {
		return // no-op: Slack disabled
	}
	payload := map[string]string{"channel": s.Channel, "text": text}
	body, err := json.Marshal(payload)
	if err != nil {
		log.Printf("slack: marshal: %v", err)
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		"https://slack.com/api/chat.postMessage", bytes.NewReader(body))
	if err != nil {
		log.Printf("slack: new request: %v", err)
		return
	}
	req.Header.Set("Authorization", "Bearer "+s.Token)
	req.Header.Set("Content-Type", "application/json; charset=utf-8")

	resp, err := s.Client.Do(req)
	if err != nil {
		log.Printf("slack: post: %v", err) // swallow
		return
	}
	defer resp.Body.Close()
	// We intentionally do not parse the response; failures are non-fatal.
}

// NopNotifier discards messages (used when Slack is intentionally disabled or
// in tests).
type NopNotifier struct{}

func (NopNotifier) Notify(string) {}

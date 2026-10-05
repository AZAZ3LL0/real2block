import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../i18n";
import { FileDrop } from "./FileDrop";
import { SegmentedControl } from "./SegmentedControl";
import { Stepper } from "./Stepper";
import { WarningList } from "./WarningList";

function renderDrop() {
  const onFile = vi.fn();
  const onReject = vi.fn();
  render(
    <FileDrop label="Skin" hint="h" dropText="Drop" chooseText="choose" accept={["image/png"]} maxBytes={10} onFile={onFile} onReject={onReject} />,
  );
  const input = screen.getByLabelText<HTMLInputElement>("Skin");
  const pick = (file: File) => {
    fireEvent.change(input, { target: { files: [file] } });
  };
  return { onFile, onReject, pick };
}

describe("FileDrop", () => {
  it("accepts a valid file", () => {
    const { onFile, pick } = renderDrop();
    pick(new File(["png"], "s.png", { type: "image/png" }));
    expect(onFile).toHaveBeenCalledOnce();
  });

  it("is one focusable control described by the hint", async () => {
    renderDrop();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    await userEvent.tab();
    expect(screen.getByLabelText("Skin")).toHaveFocus();
    expect(screen.getByLabelText("Skin")).toHaveAccessibleDescription("h");
  });

  it("rejects wrong type and oversize files", () => {
    const { onFile, onReject, pick } = renderDrop();
    pick(new File(["jpg"], "s.jpg", { type: "image/jpeg" }));
    pick(new File(["x".repeat(11)], "big.png", { type: "image/png" }));
    expect(onReject.mock.calls).toEqual([["type"], ["size"]]);
    expect(onFile).not.toHaveBeenCalled();
  });
});

describe("SegmentedControl", () => {
  it("is a radio group that reports the choice", async () => {
    const onChange = vi.fn();
    const options = [{ value: "a", label: "A" }, { value: "b", label: "B" }] as const;
    render(<SegmentedControl label="Pick" value="a" onChange={onChange} options={options} />);
    expect(screen.getByRole("radio", { name: "A" })).toHaveAttribute("aria-checked", "true");
    await userEvent.click(screen.getByRole("radio", { name: "B" }));
    expect(onChange).toHaveBeenCalledWith("b");
  });
});

describe("SegmentedControl keyboard", () => {
  const options = [{ value: "a", label: "A" }, { value: "b", label: "B" }, { value: "c", label: "C" }] as const;

  function Controlled({ onChange }: { onChange: (v: string) => void }) {
    const [value, setValue] = useState<"a" | "b" | "c">("a");
    return (
      <SegmentedControl
        label="Pick"
        value={value}
        onChange={(v) => {
          setValue(v);
          onChange(v);
        }}
        options={options}
      />
    );
  }

  it("is a single tab stop on the checked option", async () => {
    render(
      <>
        <Controlled onChange={vi.fn()} />
        <button type="button">after</button>
      </>,
    );
    await userEvent.tab();
    expect(screen.getByRole("radio", { name: "A" })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("button", { name: "after" })).toHaveFocus();
  });

  it("moves the choice and the focus with arrows, Home and End, wrapping around", async () => {
    const onChange = vi.fn();
    render(<Controlled onChange={onChange} />);
    await userEvent.tab();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("radio", { name: "B" })).toHaveFocus();
    await userEvent.keyboard("{End}");
    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByRole("radio", { name: "A" })).toHaveFocus();
    await userEvent.keyboard("{ArrowLeft}");
    await userEvent.keyboard("{Home}");
    expect(onChange.mock.calls).toEqual([["b"], ["c"], ["a"], ["c"], ["a"]]);
    expect(screen.getByRole("radio", { name: "A" })).toHaveAttribute("aria-checked", "true");
  });

  it("ties a visible label to the group", () => {
    render(<SegmentedControl showLabel label="Paper" value="a" onChange={vi.fn()} options={options} />);
    expect(screen.getByText("Paper")).toBeVisible();
    expect(screen.getByRole("radiogroup", { name: "Paper" })).toBeInTheDocument();
  });
});

describe("Stepper", () => {
  it("marks the current step", () => {
    render(<Stepper label="Steps" steps={["One", "Two"]} current={1} />);
    expect(screen.getByText("Two").closest("li")).toHaveAttribute("aria-current", "step");
  });

  it("is a labelled list", () => {
    render(<Stepper label="Steps" steps={["One", "Two"]} current={0} />);
    expect(screen.getByRole("list", { name: "Steps" })).toBeInTheDocument();
  });
});

describe("WarningList", () => {
  it("shows human-readable warnings", () => {
    render(
      <I18nProvider initial="en">
        <WarningList warnings={["TORSO_NOT_VISIBLE"]} />
      </I18nProvider>,
    );
    expect(screen.getByText(/pick the shirt color manually/)).toBeInTheDocument();
  });
});
